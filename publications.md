---
title: Publications
---

<!-- Search Box -->
<input type="text" id="search-box" placeholder="Search text, fields, or tags (e.g., plumed, journal:nucleic, or #preprint)" aria-describedby="match-count">
<div id="search-summary">
  <span id="search-status">
    <span id="match-count" role="status" aria-live="polite"></span>
    <button type="button" id="clear-search" hidden>Clear search</button>
  </span>
  <a id="download-csv" href="{{ '/publications.csv' | relative_url }}" download>Download CSV</a>
</div>
<details id="search-tips">
  <summary>Search tips</summary>
  <div id="search-tip-content">
    <div id="search-tip-intro">
      <span>Frequent matches — click a suggestion to refine the current search</span>
      <label id="suggestion-weighting" title="Uncheck to use only a 1% yearly recency preference">
        (<input type="checkbox" id="favor-recent" checked>
        favor recent publications)
      </label>
    </div>
    <div id="search-tip-facets"></div>
  </div>
</details>

<!-- Posts List -->
<!-- Posts List -->
<div id="posts-container" style="display: none;">
  {% for post in site.data.publications %}
    {% assign publication_authors = post.authors | split: ", " %}
    {% capture searchable_authors %}{% for author in publication_authors %}{{ author }}{% if post.corresponding_author_positions contains forloop.index %}*{% endif %}{% unless forloop.last %}, {% endunless %}{% endfor %}{% endcapture %}
    {% capture corresponding_authors %}{% for author in publication_authors %}{% if post.corresponding_author_positions contains forloop.index %}{{ author }}|{% endif %}{% endfor %}{% endcapture %}
    {% capture publication_tags %}{% for tag in post.tags %}#{{ tag | remove_first: '#' }}|{% endfor %}{% endcapture %}
    <div class="post-data"
         data-text="{{ searchable_authors | strip | escape }} {{ post.title | escape }} {{ post.journal | escape }} {{ post.volume }} {{ post.page }} {{ post.year }} {{ post.doi }} {{ post.handle }} {{ post.arxiv }} {{ post.biorxiv }} {{ post.tags | escape }}"
         data-author="{{ searchable_authors | strip | escape }}"
         data-corresponding-author="{{ corresponding_authors | escape }}"
         data-title="{{ post.title | escape }}"
         data-journal="{{ post.journal | escape }}"
         data-tags="{{ publication_tags | escape }}"
         data-year="{{ post.year }}">
      <!-- Authors, Title, and Citation -->
      <p class="publication-details">
        <span class="publication-authors">{% for author in publication_authors %}{{ author | escape }}{% if post.corresponding_author_positions contains forloop.index %}<span title="Corresponding author" aria-label=" corresponding author">*</span>{% endif %}{% unless forloop.last %}, {% endunless %}{% endfor %}</span>
        <span class="publication-title"><strong>{{ post.title | safe }}</strong></span>
        <span class="publication-citation">
          {% if post.journal %}
            <a href="./publications?query=JOURNAL%3A%3D%22{{ post.journal | url_encode }}%22" class="journal-filter" title="Show all publications in {{ post.journal | escape }}">{{ post.journal | escape }}</a>{% if post.volume %} {{ post.volume }}{% if post.page %},{% endif %}{% endif %}{% if post.page %} {{ post.page }}{% endif %}{% if post.year %} ({{ post.year }}){% endif %}
          {% elsif post.arxiv %}
            arXiv:{{ post.arxiv }}
          {% elsif post.biorxiv %}
            biorxiv:{{ post.biorxiv }}
          {% else %}
            {{ post.citation | safe }}
          {% endif %}
        </span>
        {% if post.tags %}
        <span class="publication-tags">
          {% for tag in post.tags %}
            <a href="./publications?query=%23{{ tag | remove_first: '#' }}" class="tag">#{{ tag | remove_first: '#' }}</a>
          {% endfor %}
        </span>
        {% endif %}
      </p>

      <!-- Links and Tags -->
      <div class="publication-links">
        {% if post.handle %}
        <a href="https://hdl.handle.net/{{ post.handle }}" target="_blank">
          <img alt="IRIS link" src="https://img.shields.io/badge/IRIS-blue">
        </a>
        {% endif %}
        {% if post.doi %}
        <a href="https://doi.org/{{ post.doi }}" target="_blank">
          <img alt="DOI link" src="https://img.shields.io/badge/DOI-green">
        </a>
        {% endif %}
        {% if post.arxiv %}
        <a href="https://arxiv.org/abs/{{ post.arxiv }}" target="_blank">
          <img alt="arXiv link" src="https://img.shields.io/badge/arXiv-red">
        </a>
        {% endif %}
        {% if post.biorxiv %}
        <a href="https://doi.org/{{ post.biorxiv }}" target="_blank">
          <img alt="bioRxiv link" src="https://img.shields.io/badge/bioRxiv-orange">
        </a>
        {% endif %}
      </div>
    </div>
  {% endfor %}
</div>





<div id="posts">
  <!-- Filtered posts will be dynamically rendered here -->
</div>

<!-- Pagination Buttons -->
<div id="pagination-controls" class="pagination-bar">
  <button id="prev-button" onclick="paginate(-1)" disabled>Previous</button>
  <button id="next-button" onclick="paginate(1)">Next</button>
</div>

<!-- Posts Per Page -->
<div id="posts-per-page-controls">
  <label for="posts-per-page">Records per page:</label>
  <select id="posts-per-page" onchange="updateMaxPosts()">
    <option value="10" selected>10</option>
    <option value="20">20</option>
    <option value="50">50</option>
  </select>
</div>

<script>
let maxPosts = 10; // Default posts per page
let skipPosts = 0; // Default start at the first post
let filteredPosts = []; // Store filtered posts after search
const facetDecaySettings = {
  all: 0.99,
  recent: 0.8
};
let selectedFacetDecay = "recent";

document.addEventListener("DOMContentLoaded", () => {
  // Fetch all posts from the hidden container
  const allPostsContainer = document.getElementById('posts-container');
  const allPosts = Array.from(allPostsContainer.querySelectorAll('.post-data'));

  const urlParams = new URLSearchParams(window.location.search);
  const query = urlParams.get("query") || "";
  maxPosts = parseInt(urlParams.get("maxPosts") || maxPosts, 10);
  skipPosts = parseInt(urlParams.get("skipPosts") || skipPosts, 10);

  document.getElementById("search-box").value = query;
  document.getElementById("posts-per-page").value = maxPosts;

  selectedFacetDecay = loadFacetDecaySetting();
  updateFacetDecayControls();
  document.getElementById("favor-recent").addEventListener("change", event => {
    setFacetDecaySetting(event.target.checked ? "recent" : "all");
  });

  // Attach the input listener to the search box
  document.getElementById("search-box").addEventListener("input", () => {
    skipPosts = 0; // Reset to the first page when search input changes
    filterPosts(allPosts);
  });

  document.getElementById("clear-search").addEventListener("click", () => {
    document.getElementById("search-box").value = "";
    skipPosts = 0;
    filterPosts(allPosts);
    document.getElementById("search-box").focus();
  });

  // Filter and render posts initially
  filterPosts(allPosts);
});

function filterPosts(allPosts) {
  const query = normalizeString(document.getElementById('search-box').value.toLowerCase());

  // Update the query parameter in the URL
  const url = new URL(window.location);
  url.searchParams.set("query", query);
  url.searchParams.set("maxPosts", maxPosts);
  url.searchParams.set("skipPosts", skipPosts);
  window.history.replaceState({}, '', url);

  // Filter posts based on the query
  filteredPosts = allPosts.filter(post => {
    const text = normalizeString(post.getAttribute('data-text').toLowerCase());
    const andGroups = splitSearchExpression(query, "&");
    return andGroups.every(andGroup => {
      const orTerms = splitSearchExpression(andGroup, "|");
      return orTerms.some(term => matchesSearchTerm(post, text, term));
    });
  });

  updateSearchTips();

  // Immediately render posts after filtering
  renderPosts();
}

function addFacetValue(facetMap, label, weight) {
  const cleanedLabel = label.trim();
  if (!cleanedLabel) return;

  const key = normalizeString(cleanedLabel.toLowerCase());
  const existing = facetMap.get(key);
  if (existing) {
    existing.count += 1;
    existing.score += weight;
  } else {
    facetMap.set(key, {
      label: cleanedLabel,
      count: 1,
      score: weight
    });
  }
}

function topFacetValues(facetMap, limit) {
  return Array.from(facetMap.values())
    .sort((a, b) =>
      b.score - a.score ||
      a.label.localeCompare(b.label)
    )
    .slice(0, limit);
}

function loadFacetDecaySetting() {
  try {
    const savedSetting = localStorage.getItem("publicationSuggestionWeighting");
    if (Object.prototype.hasOwnProperty.call(facetDecaySettings, savedSetting)) return savedSetting;
  } catch (error) {
    // Suggestions still work when browser storage is unavailable.
  }
  return "recent";
}

function updateFacetDecayControls() {
  document.getElementById("favor-recent").checked = selectedFacetDecay === "recent";
}

function setFacetDecaySetting(setting) {
  if (!Object.prototype.hasOwnProperty.call(facetDecaySettings, setting)) return;

  selectedFacetDecay = setting;
  updateFacetDecayControls();
  try {
    localStorage.setItem("publicationSuggestionWeighting", setting);
  } catch (error) {
    // Keep the setting for this page view when browser storage is unavailable.
  }
  updateSearchTips();
}

function facetWeightForPublication(post) {
  const publicationYear = Number.parseInt(post.dataset.year, 10);
  const currentYear = new Date().getFullYear();
  const age = Number.isFinite(publicationYear)
    ? Math.max(0, currentYear - publicationYear)
    : 0;
  return facetDecaySettings[selectedFacetDecay] ** age;
}

function quotedSearchValue(value) {
  return `"${value.replace(/"/g, "")}"`;
}

function appendSearchTerm(term) {
  const searchBox = document.getElementById("search-box");
  const currentQuery = searchBox.value.trim();
  searchBox.value = currentQuery ? `${currentQuery}&${term}` : term;
  searchBox.dispatchEvent(new Event("input", { bubbles: true }));
  searchBox.focus();
}

function addSearchTipRow(container, heading, values, termForValue) {
  if (values.length === 0) return;

  const row = document.createElement("div");
  row.className = "search-tip-row";

  const label = document.createElement("span");
  label.className = "search-tip-label";
  label.textContent = `${heading}:`;
  row.appendChild(label);

  values.forEach(value => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "search-tip";
    button.textContent = `${value.label} (${value.count})`;
    button.addEventListener("click", () => appendSearchTerm(termForValue(value)));
    row.appendChild(button);
  });

  container.appendChild(row);
}

function updateSearchTips() {
  const facets = document.getElementById("search-tip-facets");
  facets.replaceChildren();

  const journals = new Map();
  const authors = new Map();
  const tags = new Map();
  let thesisCount = 0;

  filteredPosts.forEach(post => {
    const weight = facetWeightForPublication(post);
    const journal = post.dataset.journal.trim();
    if (normalizeString(journal.toLowerCase()) === "phd thesis") {
      thesisCount += 1;
    } else {
      addFacetValue(journals, journal, weight);
    }

    // A trailing star marks corresponding authorship, which is deliberately
    // ignored when building general author suggestions.
    const postAuthors = new Set(
      post.dataset.author.split(",")
        .map(author => author.trim().replace(/\*$/, ""))
        .filter(Boolean)
    );
    postAuthors.forEach(author => addFacetValue(authors, author, weight));

    const postTags = new Set(post.dataset.tags.split("|").filter(Boolean));
    postTags.forEach(tag => addFacetValue(tags, tag, weight));
  });

  addSearchTipRow(facets, "Journals", topFacetValues(journals, 3), value =>
    `journal:=${quotedSearchValue(value.label)}`
  );

  if (thesisCount > 0) {
    addSearchTipRow(facets, "Type", [{
      label: "PHD THESIS",
      count: thesisCount
    }], value => `journal:=${quotedSearchValue(value.label)}`);
  }

  addSearchTipRow(facets, "Authors", topFacetValues(authors, 4), value =>
    `author:${quotedSearchValue(value.label)}`
  );
  addSearchTipRow(facets, "Tags", topFacetValues(tags, 4), value => value.label);

  if (!facets.hasChildNodes()) {
    facets.textContent = "No refinements are available for this selection.";
  }
}

function splitSearchExpression(expression, separator) {
  const parts = [];
  let current = "";
  let inQuotes = false;

  for (const character of expression) {
    if (character === '"') {
      inQuotes = !inQuotes;
    }

    if (character === separator && !inQuotes) {
      parts.push(current);
      current = "";
    } else {
      current += character;
    }
  }

  parts.push(current);
  return parts;
}

function matchesSearchTerm(post, text, rawTerm) {
  const term = rawTerm;
  const fieldSearch = term.match(/^(author|authors|title|journal|journals|year)(:=|=:|:)(.*)$/);

  if (!fieldSearch) {
    return text.includes(term);
  }

  const aliases = { authors: "author", journals: "journal" };
  const field = aliases[fieldSearch[1]] || fieldSearch[1];
  let searchValue = fieldSearch[3];

  if (searchValue.startsWith('"') && searchValue.endsWith('"')) {
    searchValue = searchValue.slice(1, -1);
  }

  if (field === "author" && searchValue.endsWith("*")) {
    searchValue = searchValue.slice(0, -1);
    const correspondingAuthors = normalizeString(
      post.dataset.correspondingAuthor.toLowerCase()
    ).split("|").filter(Boolean);

    if (fieldSearch[2] === ":") {
      return correspondingAuthors.some(author => author.includes(searchValue));
    }

    return correspondingAuthors.some(author => author === searchValue);
  }

  const value = normalizeString(post.dataset[field].toLowerCase());

  if (fieldSearch[2] === ":") {
    return value.includes(searchValue);
  }

  return value === searchValue;
}

function updateSearchSummary(start, end) {
  const count = filteredPosts.length;
  const visibleStart = count === 0 ? 0 : start + 1;
  const visibleEnd = Math.min(end, count);
  document.getElementById('match-count').textContent =
    `Displaying ${visibleStart}\u2013${visibleEnd} of ${count} ${count === 1 ? 'match' : 'matches'}`;
  document.getElementById('clear-search').hidden =
    document.getElementById('search-box').value.trim() === "";
}

function normalizeString(str) {
  if (str.normalize) {
    // Modern browsers: Use Unicode normalization
    return str.normalize("NFD").replace(/[\u0300-\u036f]/g, "");
  } else {
    // Fallback: Manual diacritic removal for older browsers
    const diacriticMap = {
      'ä': 'a', 'á': 'a', 'à': 'a', 'ã': 'a', 'â': 'a', 'å': 'a', 'ā': 'a',
      'ö': 'o', 'ó': 'o', 'ò': 'o', 'õ': 'o', 'ô': 'o', 'ø': 'o', 'ō': 'o',
      'ü': 'u', 'ú': 'u', 'ù': 'u', 'ũ': 'u', 'û': 'u', 'ū': 'u',
      'ë': 'e', 'é': 'e', 'è': 'e', 'ẽ': 'e', 'ê': 'e', 'ē': 'e',
      'ï': 'i', 'í': 'i', 'ì': 'i', 'ĩ': 'i', 'î': 'i', 'ī': 'i',
      'ç': 'c', 'ñ': 'n', 'ÿ': 'y', 'ß': 'ss'
    };
    return str.split('').map(char => diacriticMap[char] || char).join('');
  }
}

function renderPosts() {
  const postsContainer = document.getElementById('posts');
  postsContainer.innerHTML = ''; // Clear current posts

  if (filteredPosts.length === 0) {
    skipPosts = 0;
  } else if (skipPosts >= filteredPosts.length) {
    skipPosts = Math.floor((filteredPosts.length - 1) / maxPosts) * maxPosts;
  }

  const start = skipPosts;
  const end = skipPosts + maxPosts;

  // Render the subset of filtered posts
  filteredPosts.slice(start, end).forEach(post => {
    const clonedPost = post.cloneNode(true); // Clone original post structure
    postsContainer.appendChild(clonedPost);
  });

  // Enable/disable pagination buttons
  document.getElementById("prev-button").disabled = skipPosts <= 0;
  document.getElementById("next-button").disabled = end >= filteredPosts.length;
  updateSearchSummary(start, end);

  // Update query parameters for pagination
  const url = new URL(window.location);
  const query = document.getElementById('search-box').value;
  url.searchParams.set("query", query);
  url.searchParams.set("maxPosts", maxPosts);
  url.searchParams.set("skipPosts", skipPosts);
  window.history.replaceState({}, '', url);
}

function paginate(direction) {
  skipPosts += direction * maxPosts;
  renderPosts();
}

function updateMaxPosts() {
  maxPosts = parseInt(document.getElementById("posts-per-page").value, 10);
  skipPosts = 0; // Reset to the first page
  renderPosts();
}

</script>


<style>

#posts {
    font-family: Arial, sans-serif;
    line-height: 1.6;
    margin: 20px auto;
    max-width: 800px;
}

#posts .post-data {
    border-bottom: 1px solid #ddd;
    padding: 10px 0;
}

#posts .post-data:last-child {
    border-bottom: none; /* Remove the border for the last post */
}

#posts .post-date {
    color: #888;
    font-size: 0.9rem;
    margin-bottom: 5px;
}

#posts .post-text {
    font-size: 1.1rem;
    margin-bottom: 10px;
}

#posts .post-link {
    text-decoration: none;
    color: #007acc;
}

#posts .post-link:hover {
    text-decoration: underline;
}

#search-box {
  margin-bottom: 0;
  padding: 10px;
  width: 100%; /* Full width */
  font-size: 16px;
}

#search-summary {
  align-items: baseline;
  color: #888;
  display: flex;
  font-size: 0.85rem;
  gap: 1rem;
  justify-content: space-between;
  margin-top: 4px;
  margin-bottom: 2px;
}

#search-tips {
  color: #888;
  font-size: 0.82rem;
  margin-bottom: 20px;
}

#search-tips summary {
  color: #999;
  cursor: pointer;
  display: inline-block;
  list-style: none;
}

#search-tips summary::-webkit-details-marker {
  display: none;
}

#search-tips summary::before {
  content: "\25b8\00a0";
}

#search-tips[open] summary::before {
  content: "\25be\00a0";
}

#search-tip-content {
  border-left: 2px solid #eee;
  margin-top: 0.4rem;
  padding: 0.15rem 0 0.15rem 0.75rem;
}

.search-tip-row {
  margin: 0.25rem 0;
}

#search-tip-intro {
  align-items: center;
  display: flex;
  flex-wrap: wrap;
  gap: 0.65rem;
  margin: 0.25rem 0 0.45rem;
}

#suggestion-weighting {
  align-items: center;
  cursor: pointer;
  display: flex;
  gap: 0.35rem;
  margin: 0;
  white-space: nowrap;
  width: fit-content;
}

#favor-recent {
  margin: 0;
}

.search-tip-label {
  font-weight: 600;
  margin-right: 0.4rem;
}

.search-tip {
  appearance: none;
  background: none;
  border: 0;
  color: #777;
  cursor: pointer;
  font: inherit;
  margin: 0 0.65rem 0.15rem 0;
  padding: 0;
  text-decoration: underline;
  text-decoration-color: #bbb;
  text-underline-offset: 2px;
}

.search-tip:hover,
.search-tip:focus-visible {
  color: #1e6bb8;
}

#download-csv {
  white-space: nowrap;
}

#clear-search {
  appearance: none;
  background: none;
  border: 0;
  color: #999;
  cursor: pointer;
  font: inherit;
  font-size: 0.78rem;
  margin-left: 0.4rem;
  padding: 0;
  text-decoration: none;
}

#clear-search:hover,
#clear-search:focus-visible {
  color: #666;
  text-decoration: underline;
}

#posts-per-page-controls {
  margin-top: 20px;
  text-align: center;
}

#pagination-controls {
  margin-top: 20px;
  text-align: center;
}

#pagination-controls button {
  background-color: white;
  border: 2px solid #1e6bb8; /* Match the blue border */
  color: #1e6bb8; /* Match the blue text */
  padding: 10px 20px;
  font-size: 16px;
  margin: 5px;
  border-radius: 5px; /* Rounded corners */
  cursor: pointer;
  transition: all 0.3s ease; /* Smooth hover effect */
}

#pagination-controls button:hover {
  background-color: #1e6bb8; /* Blue background on hover */
  color: white; /* White text on hover */
}

#pagination-controls button:disabled {
  background-color: #ccc; /* Gray background for disabled state */
  color: #666; /* Slightly darker gray text */
  cursor: not-allowed;
}

.pagination-bar {
  border-top: 1px solid #ddd; /* Horizontal line */
  padding-top: 10px; /* Add spacing between the line and the buttons */
  margin-top: 20px; /* Add spacing from the last post */
}

/* Compact Layout Styling */
/* Compact authors, title, and citation in a single line */
/* Overall font adjustment */
body {
  font-size: 16px; /* Adjust the base font size */
}

/* Compact authors, title, and citation in a single line */
.publication-details {
  font-size: 1rem; /* Slightly larger */
  color: #333;
  line-height: 1.6;
}

/* Align links and tags in a row */
.publication-links {
  display: flex;
  align-items: center;
  flex-wrap: wrap; /* Ensure proper layout on smaller screens */
  gap: 10px; /* Space between badges and tags */
}

.publication-links img {
  margin-right: 5px;
}

.publication-tags {
  color: #007acc;
}

.publication-tags a {
  margin-right: 5px;
  text-decoration: none;
}

.publication-tags a:hover {
  text-decoration: underline;
}

/* Add more spacing between articles */
.post-data {
  margin-bottom: 25px; /* Increased spacing between entries */
  border-bottom: 1px solid #ddd; /* Separator for clarity */
  padding-bottom: 15px;
}



</style>
