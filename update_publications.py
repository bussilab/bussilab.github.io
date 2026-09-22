

import csv
import os
import yaml
import requests
import re
import tqdm
from bs4 import BeautifulSoup
from xml.etree import ElementTree
from dateutil import parser

user_agent="IRIS metadata fetch (contact: bussi@sissa.it)"

csv_fields = (
    "authors", "title", "journal", "volume", "page", "year",
    "publication_type", "issn", "isbn", "doi", "handle", "arxiv",
    "biorxiv", "tags"
)

issn_pattern = re.compile(r"(?<!\d)(\d{4}-\d{3}[\dXx])(?!\d)")


def infer_publication_type(record):
    """Infer a normalized publication type from the stored metadata."""
    tags = set(record.get("tags", []))
    if "#review" in tags:
        return "review"
    if "#bookchapter" in tags:
        return "book chapter"
    if "#proceedings" in tags:
        return "conference proceedings"
    if "#preprint" in tags:
        return "preprint"
    if record.get("journal"):
        return "journal article"
    return ""


def format_authors_with_corresponding_markers(publication):
    """Add a trailing * to corresponding authors in an exported author list."""
    authors = publication.get("authors", "")
    if not authors:
        return authors

    author_list = authors.split(", ")
    positions = set(publication.get("corresponding_author_positions", []))
    if positions and (min(positions) < 1 or max(positions) > len(author_list)):
        raise RuntimeError(
            f"Invalid corresponding-author position for {publication.get('handle', '')}"
        )

    return ", ".join(
        author + ("*" if position in positions else "")
        for position, author in enumerate(author_list, start=1)
    )


def write_publications_csv(publications, path="publications.csv"):
    """Write the website publication data as an Excel-friendly CSV file."""
    with open(path, "w", encoding="utf-8-sig", newline="") as csv_file:
        writer = csv.DictWriter(
            csv_file,
            fieldnames=csv_fields,
            lineterminator="\n",
        )
        writer.writeheader()
        for publication in publications:
            row = {field: publication.get(field, "") for field in csv_fields}
            row["authors"] = format_authors_with_corresponding_markers(publication)
            row["publication_type"] = (
                publication.get("publication_type")
                or infer_publication_type(publication)
            )
            row["tags"] = " ".join(publication.get("tags", []))
            writer.writerow(row)

def extract_authors(raw_data):
    """Extract list of authors from IRIS raw data."""
    def surname_only(value):
        # A few IRIS surname fields include trailing initials (for example,
        # "Bonomi M." or "Tribello G. A.").  Remove only final one-letter
        # initials so author searches remain consistent across records.
        return re.sub(r"(?:\s+[^\W\d_]\.)+$", "", value.strip())

    authors = [surname_only(item[1]) for item in raw_data if item[0] == "scopus.contributor.surname"]
    if len(authors)!=0:
        return authors
    authors = [surname_only(item[1]) for item in raw_data if item[0] == "isi.contributor.surname"]
    if len(authors)!=0:
        return authors
    #authors = [item[1].split()[0].rstrip(",") for item in raw_data if item[0] == "dc.authority.people"]
    authors = [surname_only(item[1].split(",")[0]) for item in raw_data if item[0] == "dc.authority.people"]
    if len(authors)!=0:
        return authors
    raise RuntimeError("Missing authors")


def extract_corresponding_author_positions(soup):
    """Return one-based positions of authors marked as corresponding in IRIS."""
    positions = []
    contributors = soup.select("span.contributor")
    for position, contributor in enumerate(contributors, start=1):
        marker = contributor.find(
            attrs={"title": re.compile(r"^Corresponding author$", re.IGNORECASE)}
        )
        if marker is not None:
            positions.append(position)
    return positions

def extract_scalar(raw_data,names):
    """Extract a scalar from IRIS raw data. Try a list of fallback names."""
    for name in names:
        fields = [item[1] for item in raw_data if item[0] == name]
        assert len(fields)<2
        if len(fields)==1:
            return fields[0]
    return ""

def extract_list(raw_data,names):
    """Extract a list from IRIS raw data. Try a list of fallback names."""
    fields = []
    for name in names:
        fields.extend([item[1] for item in raw_data if item[0] == name])
    return fields

def thesis_record_from_iris(record):
    """Build the minimal publication record needed for a PhD thesis."""
    raw_data = record["iris_raw"]
    authors = extract_authors(raw_data)
    title = extract_scalar(raw_data, ["dc.title"])
    issued = extract_scalar(raw_data, ["dc.date.issued"])
    accession_date = extract_scalar(raw_data, ["dc.date.accessioned"])
    year_match = re.search(r"\b\d{4}\b", issued)

    if not authors:
        raise RuntimeError(f"Missing thesis author for {record['handle']}")
    if not title:
        raise RuntimeError(f"Missing thesis title for {record['handle']}")
    if not year_match:
        raise RuntimeError(f"Missing thesis publication year for {record['handle']}")

    # Older IRIS records use normal capitalization while newer ones sometimes
    # store the entire name in uppercase.
    surname = authors[0]
    if surname.isupper():
        surname = surname.title()

    return {
        "authors": [surname],
        "title": title,
        "journal": "PHD THESIS",
        "year": year_match.group(0),
        "accession_date": accession_date,
        "publication_type": "PhD thesis",
        "handle": record["handle"],
    }

def extract_issn(raw_data):
    """Extract the print ISSN without falling back to electronic ISSN fields."""
    field_groups = (
        (
            "dc.identifier.issn",
            "isi.identifier.issn",
            "scopus.identifier.issn",
        ),
        (
            "isi.authority.ancejournal",
            "scopus.authority.ancejournal",
            "dc.authority.ancejournal",
        ),
    )
    for field_names in field_groups:
        for key, value in raw_data:
            if key in field_names:
                match = issn_pattern.search(value)
                if match:
                    return match.group(1).upper()

    for key, value in raw_data:
        if key == "dc.identifier.citation":
            match = re.search(
                r"(?<![\w-])ISSN\s*:?[\s-]*(\d{4}-\d{3}[\dXx])(?!\d)",
                value,
                re.IGNORECASE,
            )
            if match:
                return match.group(1).upper()
    return ""


def extract_isbn(raw_data):
    """Extract all distinct ISBNs, preferring the curated DC metadata."""
    for field_names in (
        ("dc.identifier.isbn",),
        ("scopus.identifier.isbn", "isi.identifier.isbn"),
    ):
        values = extract_list(raw_data, field_names)
        if not values:
            continue

        # IRIS can contain the same ISBN both with and without hyphens.
        unique_values = []
        normalized_values = set()
        for value in values:
            value = value.strip()
            normalized = re.sub(r"[-\s]", "", value).upper()
            if value and normalized not in normalized_values:
                unique_values.append(value)
                normalized_values.add(normalized)
        return "; ".join(unique_values)

    return ""

def parse_raw_iris_data(raw_data,grants=None):
    """Parse IRIS raw data, returning a canonical dictionary."""

    record={}

    if grants is None:
        grants = []

    doi=extract_scalar(raw_data,[
        "dc.identifier.doi"
    ])

    if doi:
        record["doi"]=doi

    authors=extract_authors(raw_data)
    if authors:
        record["authors"]=authors
    
    title=extract_scalar(raw_data,[
        "scopus.title",
        "dc.title"
    ])
    if title:
        record["title"]=title
        
    # IRIS rewrites dc.date.firstsubmission when an existing record is edited.
    # dc.date.accessioned is stable, so metadata corrections do not reorder the
    # publication list within a year.
    accession_date=extract_scalar(raw_data,[
        "dc.date.accessioned"
        ])
    if accession_date:
        record["accession_date"]=accession_date

    year=extract_scalar(raw_data,[
        "scopus.date.issued",
        "dc.date.issued"
    ])
    if year:
        record["year"]=year
        
    journal=extract_scalar(raw_data,[
        "isi.journal.journaltitle",
        "dc.authority.ancejournal",
        "dc.relation.ispartofbook"
    ])
    if journal:
        record["journal"]=journal

    issn=extract_issn(raw_data)
    if issn:
        record["issn"]=issn

    isbn=extract_isbn(raw_data)
    if isbn:
        record["isbn"]=isbn

    
    volume=extract_scalar(raw_data,[
        "dc.relation.volume",
        "scopus.relation.volume"
    ])
    if volume:
        record["volume"]=volume
    
    page=extract_scalar(raw_data,[
        "dc.relation.articlenumber",
        "dc.relation.firstpage",
        "scopus.relation.article",
        "scopus.relation.firstpage"
    ])
    if page:
        record["page"]=page

    collection_name=extract_scalar(raw_data,[
        "dc.collection.name"
    ])
    
    if collection_name and ( "review in journal" in collection_name.lower() or "critique in journal" in collection_name.lower()):
        record["is_review"]=True

    if collection_name and "book chapter" in collection_name.lower():
        record["is_book_chapter"]=True

    if collection_name and "abstract" in collection_name.lower():
        record["is_abstract"]=True

    if collection_name and "conference proceedings" in collection_name.lower():
        record["is_conference_proceedings"]=True
    
    lista=[item for item in raw_data if re.search(r"https?://arxiv\.org/(abs|pdf)/", item[1])]
    if len(lista)>0:
        match = re.search(r"https?://arxiv\.org/(?:abs|pdf)/([^\s]+)", lista[0][1])
        if match:
            # remove .pdf and version
            record["arxiv"] = re.sub(r'v\d+$', '', match.group(1).replace(".pdf", ""))

    dc_description_note	= extract_scalar(raw_data,[
        "dc.description.note"
    ])

    dc_authority_project_list = extract_list(raw_data,[
        "dc.authority.project"
    ])

    record["grants"]=[]
    for grant in grants:
      if "strings" in grant:
          for regex in grant["strings"]:
             if regex in dc_description_note and not grant["tag"] in record["grants"]:
                 record["grants"].append(grant["tag"])
                 break
             for dc_authority_project in dc_authority_project_list:
                 if regex in dc_authority_project and not grant["tag"] in record["grants"]:
                     record["grants"].append(grant["tag"])
                     break

    ## not sure this is ok, this prefix might be not unique to biorxiv
    #lista=[item for item in raw_data if item[0]=="dc.identifier.url" and "doi.org/10.1101/" in item[1]]
    #if len(lista)>0:
    #    url=lista[0][1]
    #    url=re.sub(".*doi.org/","",url)
    #    url=re.sub("v.*","",url)
    #    record["biorxiv"]=url
    
    lista=[item for item in raw_data if item[0]=="dc.identifier.url" and "biorxiv" in item[1]]
    if len(lista)>0:
        url=lista[0][1]
        url=re.sub(".*content/","",url)
        url=re.sub("v.*","",url)
        record["biorxiv"]=url

    return record
    
def iris_get(handle,*,base_url="https://iris.sissa.it/handle/",raw=False,parsed=True,grants=None):
    url=f"{base_url}{handle}?mode=full"
    response=requests.get(url,headers={"User-Agent":user_agent})
    if response.status_code != 200:
        raise RuntimeError(response.status_code)
        
    if grants is None:
        grants=[]
    soup = BeautifulSoup(response.text,"html.parser")
    # Extract data
    raw_data = []
    rows = soup.find_all('tr')  # Find all table rows
    
    for row in rows:
        # Extract table data cells
        cells = row.find_all('td')
        if len(cells) >= 3:
            # Use the first cell as the key and the second cell as the value
            key = cells[0].text.strip()  # Metadata label
            value = cells[1].text.strip()  # Metadata value
            # remove this, which is just noise from the webpage
            if "\nVisualizza/Apri" in key:
                continue
            # Add to list
            raw_data.append((key,value))
    record={}
    if parsed:
        record=parse_raw_iris_data(raw_data,grants)
        corresponding_author_positions = extract_corresponding_author_positions(soup)
        if corresponding_author_positions:
            if max(corresponding_author_positions) > len(record.get("authors", [])):
                raise RuntimeError(
                    f"Corresponding-author position exceeds author count for {handle}"
                )
            record["corresponding_author_positions"] = corresponding_author_positions
    if raw:
        record["iris_raw"]=raw_data
    record["handle"]=handle
    return record

import requests
from bs4 import BeautifulSoup

def get_arxiv_ids_from_author_page(orcid):
    """
    Extract arXiv identifiers from the author page associated with a given ORCID.

    Parameters:
        orcid (str): ORCID ID, e.g., "0000-0001-9216-5782"

    Returns:
        List[str]: List of arXiv identifiers (e.g., ["2303.09372", "1812.08213"])
    """
    url = f"https://arxiv.org/a/{orcid}.html"
    try:
        response = requests.get(url)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        arxiv_ids = []
        for dt in soup.find_all("dt"):
            id_tag = dt.find("a", href=True)
            if id_tag and id_tag["href"].startswith("/abs/"):
                arxiv_id = id_tag["href"].split("/abs/")[1]
                arxiv_ids.append(arxiv_id)

        return arxiv_ids
    except Exception as e:
        print(f"Error: {e}")
        return []


def fetch_arxiv_metadata(arxiv_ids):
    # Base URL for arXiv API
    base_url = "http://export.arxiv.org/api/query"

    # Request all IDs in a single API call.
    arxiv_ids = list(dict.fromkeys(arxiv_ids))
    if not arxiv_ids:
        return {}
    
    # Make the GET request
    response = requests.get(base_url, params={
        "id_list": ",".join(arxiv_ids),
        "max_results": len(arxiv_ids),
    }, timeout=30)
    if response.status_code != 200:
        raise RuntimeError(f"Error: Unable to fetch data for arXiv IDs {', '.join(arxiv_ids)}")
    
    # Parse the XML response
    root = ElementTree.fromstring(response.content)
    
    # Extract title and authors, mapping each entry back to its requested ID.
    ns = {'atom': 'http://www.w3.org/2005/Atom'}  # Namespace for Atom feed
    requested_ids = {
        re.sub(r"v\d+$", "", arxiv_id): arxiv_id
        for arxiv_id in arxiv_ids
    }
    metadata = {}
    for entry in root.findall('atom:entry', ns):
        entry_id = entry.find('atom:id', ns).text.strip()
        entry_id = re.sub(r"^https?://arxiv\.org/abs/", "", entry_id)
        requested_id = requested_ids.get(re.sub(r"v\d+$", "", entry_id))
        if requested_id is None:
            continue

        title = entry.find('atom:title', ns).text.strip()
        authors = [
            author.find('atom:name', ns).text.strip().split()[-1]
            for author in entry.findall('atom:author', ns)
        ]
        metadata[requested_id] = {
            "title": title,
            "authors": authors,
        }

    missing_ids = [arxiv_id for arxiv_id in arxiv_ids if arxiv_id not in metadata]
    if missing_ids:
        raise RuntimeError(f"Missing metadata for arXiv IDs {', '.join(missing_ids)}")

    return metadata

def fetch_arxiv_metadata_with_cache(arxiv_ids, cache_path="_data/publications.yml"):
    """Fetch an arXiv batch, falling back to the current publication data."""
    try:
        return fetch_arxiv_metadata(arxiv_ids)
    except (requests.RequestException, RuntimeError, ElementTree.ParseError) as error:
        try:
            with open(cache_path) as f:
                publications = yaml.safe_load(f) or []
        except FileNotFoundError:
            raise RuntimeError(
                f"arXiv request failed and cache file {cache_path} was not found"
            ) from error

        cached_metadata = {
            publication["arxiv"]: {
                "title": publication["title"],
                "authors": publication["authors"],
            }
            for publication in publications
            if publication.get("arxiv") in arxiv_ids
            and publication.get("title")
            and publication.get("authors")
        }
        missing_ids = [
            arxiv_id for arxiv_id in arxiv_ids
            if arxiv_id not in cached_metadata
        ]
        if missing_ids:
            raise RuntimeError(
                "arXiv request failed and cached metadata is missing for "
                + ", ".join(missing_ids)
            ) from error

        warning = f"arXiv request failed ({error}); using cached metadata"
        print(f"Warning: {warning}")

        cache_marker = os.environ.get("ARXIV_CACHE_MARKER")
        if cache_marker:
            with open(cache_marker, "w") as f:
                print(warning, file=f)

        return cached_metadata

def fetch_biorxiv_metadata(doi):
    """Fetch title and author surnames for a bioRxiv DOI.

    New bioRxiv records use the openRxiv ``10.64898`` DOI prefix, which is
    not supported by the legacy api.biorxiv.org details endpoint.  DOI
    content negotiation works for both the new prefix and historical
    ``10.1101`` records and returns structured CSL-JSON metadata.
    """
    try:
        response = requests.get(
            f"https://doi.org/{doi}",
            headers={
                "Accept": "application/vnd.citationstyles.csl+json",
                "User-Agent": user_agent,
            },
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()
    except (requests.RequestException, ValueError) as error:
        raise RuntimeError(
            f"Unable to fetch bioRxiv metadata for DOI {doi}"
        ) from error

    if not isinstance(data, dict):
        raise RuntimeError(
            f"Invalid bioRxiv metadata returned for DOI {doi}"
        )

    title = data.get("title")
    # Some metadata providers use the Crossref API's one-element title list
    # even when returning CSL-JSON.
    if isinstance(title, list):
        title = title[0] if title else ""

    authors = []
    for author in data.get("author", []):
        surname = author.get("family") or author.get("literal")
        if surname:
            authors.append(surname.strip())

    if not isinstance(title, str) or not title.strip() or not authors:
        raise RuntimeError(
            f"Incomplete bioRxiv metadata returned for DOI {doi}"
        )

    return {
        "title": title.strip(),
        "authors": authors,
    }

def iris_fetch_handles(author_name, max_pages=10):
    base_url = "https://iris.sissa.it/simple-search"
    params_template = {
        "filter_field": "author",
        "filter_type": "contains",
        "filter_value": author_name,
        "filter_value_display": author_name,
        "rpp": 100,
        "sort_by": "dc.date.issued_dt",
        "order": "DESC",
        "submit_search": "Aggiorna",
        "start": 0
    }
    
    all_handles = []
    for page in range(max_pages):
        # Update the "start" parameter for pagination
        params_template["start"] = page * 100
        
        # Make the request
        response = requests.get(base_url, params=params_template, headers={"User-Agent":user_agent})
        
        if response.status_code != 200:
            print(f"Error fetching page {page}: {response.status_code}")
            break
        
        # Search for "handle" in the response text
        handles = re.findall(r'<a href="/handle/([^"]+)"', response.text)
        if not handles:
            print(f"No more handles found on page {page}. Stopping.")
            break
        
        all_handles.extend(handles)
        print(f"Fetched {len(handles)} handles from page {page}.")
    
    return all_handles

def citation_to_yaml(record):
    output={}
    tags=[]
    # we skip abstracts
    if "is_abstract" in record and record["is_abstract"]:
        return None

    if "authors" in record:
        if isinstance(record["authors"],str):
            output["authors"]=record["authors"]
        else:
            output["authors"]=", ".join(record["authors"])
    if "title" in record:
        output["title"]=record["title"]
    if "corresponding_author_positions" in record:
        output["corresponding_author_positions"] = record[
            "corresponding_author_positions"
        ]

    # Keep bibliographic fields separate. The website assembles their visual
    # representation, while the individual values remain available for search.
    for field in (
        "journal", "volume", "page", "year", "publication_type", "issn",
        "isbn",
    ):
        if field in record:
            output[field]=record[field]
        
    if "arxiv" in record:    
        output["arxiv"]=record["arxiv"]
    if "biorxiv" in record: 
        output["biorxiv"]=record["biorxiv"]

    if not "journal" in record:
        if "arxiv" in record or "biorxiv" in record:
            tags.append("#preprint")
    if "is_book_chapter" in record and record["is_book_chapter"]:
        tags.append("#bookchapter")
    if "is_review" in record and record["is_review"]:
        tags.append("#review")
    if "is_conference_proceedings" in record and record["is_conference_proceedings"]:
        tags.append("#proceedings")

    if "grants" in record:
        for grant in record["grants"]:
            tags.append("#"+grant)

    if "doi" in record:
        output["doi"]=record["doi"]
    if "handle" in record:
        output["handle"]=record["handle"]
        
    if tags:
        output["tags"]=tags
        
    return output

def sort_database(biblio_list):
    """
    Sort bibliography entries:
    1. Items without 'year' come first.
    2. Items with 'year' are sorted in decreasing year order.
    3. Within each group, items are sorted by most recent accession_date.
       These without accession_date are placed first
    4. Finally, items are sorted alphabetically by 'title'
    """

    def sort_key(item):
        # Check if 'year' exists; if not, assign a default high value (e.g., None comes before any year)
        year = item.get("year")
        title = item.get("title", "")
        accession_date = item.get("accession_date", "3000/01/01").strip()

        try:
            date_obj = parser.parse(accession_date)
            timestamp = -date_obj.timestamp()
        except Exception:
            timestamp = float('inf')

        return (year is not None,
                -int(year) if year else 0,
                timestamp,
                title.lower())

    # Sort using the custom key
    return sorted(biblio_list, key=sort_key)


if __name__ == "__main__":

    # fetch all material from IRIS
    handles = iris_fetch_handles("Bussi")

    # here we could manually add handles
    # handles.append("xxxx/xxx")
    with open("_data/grants.yml") as f:
        grants=yaml.safe_load(f)
    
    try:
        with open("_data/publication_extras.yml") as f:
            publication_extras=yaml.safe_load(f)
    except FileNotFoundError:
        publication_extras=[]

    with open("_data/people.yml") as f:
        people=yaml.safe_load(f)

    thesis_handles = [person["thesis"] for person in people if "thesis" in person]
    thesis_handle_set = set(thesis_handles)

    preprints = [p for p in publication_extras if "arxiv" in p or "biorxiv" in p]

    orcid_arxiv_ids = get_arxiv_ids_from_author_page("0000-0001-9216-5782")

    for arxiv_id in orcid_arxiv_ids:
        if arxiv_id not in [p["arxiv"] for p in preprints if "arxiv" in p]:
            preprints.append({"arxiv": arxiv_id})

    add_handles = [p["handle"] for p in publication_extras if "handle" in p]
    handles += [h for h in add_handles if h not in handles]
    handles += [h for h in thesis_handles if h not in handles]

    database=[]
    for handle in tqdm.tqdm(handles):
        if handle in thesis_handle_set:
            record = iris_get(handle,raw=True,parsed=False)
            database.append(thesis_record_from_iris(record))
        else:
            database.append(iris_get(handle,raw=True,grants=grants))
        
    for item in preprints:
        if "arxiv" in item:
            if not item["arxiv"] in [item["arxiv"] for item in database if "arxiv" in item]:
                database = [item] + database
        elif "biorxiv" in item:
            if not item["biorxiv"] in [item["biorxiv"] for item in database if "biorxiv" in item]:
                database = [item] + database
    
    arxiv_ids = [
        item["arxiv"] for item in database
        if "arxiv" in item and "handle" not in item
    ]
    arxiv_metadata = fetch_arxiv_metadata_with_cache(arxiv_ids)

    for item in tqdm.tqdm(database):
        if "arxiv" in item and "handle" not in item:
            item |= arxiv_metadata[item["arxiv"]]
        if "biorxiv" in item and "handle" not in item:
            item |= fetch_biorxiv_metadata(item["biorxiv"])

    # override using local yml

    for item in database:
        for extra in publication_extras:
            if "handle" in item and "handle" in extra and item["handle"] == extra["handle"]:
                    for k in extra.keys():
                        item[k] = extra[k]
        
    database=sort_database(database)
    
    publications=[]
    for item in database:
        citation=citation_to_yaml(item)
        if citation:
            publications.append(citation)
        
    with open("_data/publications.yml","w") as f:
        yaml.safe_dump(publications, f)

    write_publications_csv(publications)
