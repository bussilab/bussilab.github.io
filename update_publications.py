

import yaml
import requests
import re
import tqdm
from bs4 import BeautifulSoup
from xml.etree import ElementTree
from dateutil import parser


def extract_authors(raw_data):
    """Extract list of authors from IRIS raw data."""
    authors = [item[1] for item in raw_data if item[0] == "scopus.contributor.surname"]
    if len(authors)!=0:
        return authors
    authors = [item[1] for item in raw_data if item[0] == "isi.contributor.surname"]
    if len(authors)!=0:
        return authors
    #authors = [item[1].split()[0].rstrip(",") for item in raw_data if item[0] == "dc.authority.people"]
    authors = [item[1].split(",")[0] for item in raw_data if item[0] == "dc.authority.people"]
    if len(authors)!=0:
        return authors
    raise RuntimeError("Missing authors")

def extract_scalar(raw_data,names):
    """Extract a scalar from IRIS raw data. Try a list of fallback names."""
    for name in names:
        fields = [item[1] for item in raw_data if item[0] == name]
        assert len(fields)<2
        if len(fields)==1:
            return fields[0]
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
        
    submission_date=extract_scalar(raw_data,[
        "dc.date.firstsubmission"
        ])
    if submission_date:
        record["submission_date"]=submission_date

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
    
    if collection_name and "review in journal" in collection_name.lower():
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
            record["arxiv"] = match.group(1).replace(".pdf", "")  # Remove .pdf if present

    dc_description_note	= extract_scalar(raw_data,[
        "dc.description.note"
    ])

    record["grants"]=[]
    for grant in grants:
      if "strings" in grant:
          for regex in grant["strings"]:
             if regex in dc_description_note:
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
    response=requests.get(f"{base_url}{handle}?mode=full")
    # Check the response status
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
    if raw:
        record["iris_raw"]=raw_data
    record["handle"]=handle
    return record


def fetch_arxiv_metadata(arxiv_id):
    # Base URL for arXiv API
    base_url = "http://export.arxiv.org/api/query"
    
    # Construct the query
    query_url = f"{base_url}?id_list={arxiv_id}"
    
    # Make the GET request
    response = requests.get(query_url)
    if response.status_code != 200:
        raise RuntimeError(f"Error: Unable to fetch data for arXiv ID {arxiv_id}")
    
    # Parse the XML response
    root = ElementTree.fromstring(response.content)
    
    # Extract title and authors
    ns = {'atom': 'http://www.w3.org/2005/Atom'}  # Namespace for Atom feed
    title = root.find('atom:entry/atom:title', ns).text.strip()
    authors = [
        author.find('atom:name', ns).text.strip().split()[-1]  # Extract only the surname
        for author in root.findall('atom:entry/atom:author', ns)
    ]
    
    return {
        "title": title,
        "authors": authors
    }
import requests

def fetch_biorxiv_metadata(doi):
    # Base URL for bioRxiv API
    base_url = "https://api.biorxiv.org/details/biorxiv"
    
    # Construct the query URL
    query_url = f"{base_url}/{doi}"
    
    # Make the GET request
    response = requests.get(query_url)
    if response.status_code != 200:
        raise RuntimeError(f"Error: Unable to fetch data for DOI {doi}")
    
    # Parse the JSON response
    data = response.json()
    
    if data["messages"][0]["status"] != "ok":
        raise RuntimeError(f"Error: DOI {doi} not found")
    
    # Extract metadata
    preprint = data["collection"][0]
    title = preprint["title"]
    authors_full = preprint["authors"]

    # Extract surnames properly
    authors_surnames = [author.split(",")[0].strip() for author in authors_full.split("; ")]
    
    return {
        "title": title,
        "authors": authors_surnames
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
        response = requests.get(base_url, params=params_template)
        
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
        output["authors"]=", ".join(record["authors"])
    if "title" in record:
        output["title"]=record["title"]
    if "journal" in record:
        citation=record["journal"]
        if "volume" in record:
            citation+=" "+record["volume"]+","
        if "page" in record:
            citation+=" "+record["page"]
        elif "doi" in record:
            citation+=" https://doi.org/"+record["doi"]
        if "year" in record:
            citation+=" (" + record["year"] + ")"
        output["citation"]=citation
    elif "arxiv" in record:
        output["citation"]="arXiv:"+record["arxiv"]    
    elif "biorxiv" in record:
        output["citation"]="biorxiv:"+record["biorxiv"]
        
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
    3. Within each group, items are sorted by most recent submission_date.
    4. Finally, items are sorted alphabetically by 'title'
    """

    def sort_key(item):
        # Check if 'year' exists; if not, assign a default high value (e.g., None comes before any year)
        year = item.get("year")
        title = item.get("title", "")
        submission_date = item.get("submission_date", "").strip()

        try:
            date_obj = parser.parse(submission_date)
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

    preprints = [p for p in publication_extras if "arxiv" in p or "biorxiv" in p]
    add_handles = [p["handle"] for p in publication_extras if "handle" in p]

    handles += [h for h in add_handles if h not in handles]

    database=[]
    for handle in tqdm.tqdm(handles):
        database.append(iris_get(handle,raw=True,grants=grants))
        
    for item in preprints:
        if "arxiv" in item:
            if not item["arxiv"] in [item["arxiv"] for item in database if "arxiv" in item]:
                database = [item] + database
        elif "biorxiv" in item:
            if not item["biorxiv"] in [item["biorxiv"] for item in database if "biorxiv" in item]:
                database = [item] + database
    
    for item in database:
        if "arxiv" in item and not "handle" in item:
            item |= fetch_arxiv_metadata(item["arxiv"])
        if "biorxiv" in item and not "handle" in item:
            item |= fetch_biorxiv_metadata(item["biorxiv"])

    database=sort_database(database)
    
    publications=[]
    for item in database:
        citation=citation_to_yaml(item)
        if citation:
            publications.append(citation)
        
    with open("_data/publications.yml","w") as f:
        print(yaml.safe_dump(publications),file=f)


