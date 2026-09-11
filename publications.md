---
title: Publications
---

<!-- Search Box -->
<input type="text" id="search-box" placeholder="Search text, fields, or tags (e.g., plumed, journal:nucleic, or #preprint)" aria-describedby="match-count">
<div id="search-summary">
  <span id="match-count" role="status" aria-live="polite"></span>
  <button type="button" id="clear-search" hidden>Clear search</button>
</div>

<!-- Posts List -->
<!-- Posts List -->
<div id="posts-container" style="display: none;">
  {% for post in site.data.publications %}
    <div class="post-data"
         data-text="{{ post.authors | escape }} {{ post.title | escape }} {{ post.journal | escape }} {{ post.volume }} {{ post.page }} {{ post.year }} {{ post.doi }} {{ post.handle }} {{ post.arxiv }} {{ post.biorxiv }} {{ post.tags | escape }}"
         data-author="{{ post.authors | escape }}"
         data-title="{{ post.title | escape }}"
         data-journal="{{ post.journal | escape }}"
         data-year="{{ post.year }}">
      <!-- Authors, Title, and Citation -->
      <p class="publication-details">
        <span class="publication-authors">{{ post.authors | safe }}</span>
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

  // Immediately render posts after filtering
  renderPosts();
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
  const value = normalizeString(post.dataset[field].toLowerCase());
  let searchValue = fieldSearch[3];

  if (searchValue.startsWith('"') && searchValue.endsWith('"')) {
    searchValue = searchValue.slice(1, -1);
  }

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
  color: #888;
  font-size: 0.85rem;
  margin-top: 4px;
  margin-bottom: 20px;
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
