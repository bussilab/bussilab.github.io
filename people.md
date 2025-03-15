---
title: People
---

<style>
.people-container {
  display: flex;
  flex-wrap: wrap;
  gap: 20px;
  justify-content: center;
  padding: 20px;
}

.person-card {
  background: #fff;
  border: 1px solid #ddd;
  border-radius: 8px;
  width: 300px;
  padding: 20px;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
  text-align: center;
}

.person-card img {
  border-radius: 50%;
  width: 100px;
  height: 100px;
  object-fit: cover;
  margin-bottom: 15px;
}

.person-info h3 {
  font-size: 1.2em;
  margin: 0 0 10px;
}

.person-role {
  font-weight: bold;
  color: #555;
  margin-bottom: 10px;
}

.person-research {
}

.person-funds {
  font-size: 0.9em;
  color: #777;
  margin-bottom: 15px;
}

.person-links a {
  color: #007acc;
  margin: 0 5px;
  font-size: 1.2em;
  text-decoration: none;
}

.person-links a:hover {
  color: #005bb5;
}

@media (max-width: 768px) {
  .people-container {
    flex-direction: column;
    align-items: center;
  }

  .person-card {
    width: 90%;
  }
}

.group-picture {
  display: block;
  max-width: 600px; /* Set a reasonable max width */
  width: 80%; /* Allow responsiveness but prevent it from being too large */
  height: auto;
  margin: 20px auto; /* Center the image */
  border-radius: 15px; /* Rounded corners */
  box-shadow: 0px 4px 10px rgba(0, 0, 0, 0.2); /* Soft shadow */
}

</style>

<img src="images/group-pic.jpg" alt="Group Picture" class="group-picture">

<div class="tabs-container">
  <button class="tab-button active" data-tab="current" onclick="filterPeople('current')">Current</button>
  <button class="tab-button" data-tab="guest" onclick="filterPeople('guest')">Guests</button>
  <button class="tab-button" data-tab="previous" onclick="filterPeople('previous')">Previous</button>
</div>


<div class="people-container">
  {% for person in site.data.people %}
  <div class="person-card" id="{{ person.name | slugify }}"
    data-role="
       {% if person.role contains 'Guest' %}guest {% endif %}
       {% if person.previously %}previous {% endif %}
       {% unless person.previously %}current{% endunless %}
    ">
    <div class="person-pic">
      {% if person.pic %}
      <img src="{{ person.pic }}" alt="Picture of {{ person.name }}">
      {% endif %}
    </div>
    <div class="person-info">
      <h3>{{ person.name }}</h3>
      <p class="person-role">{% if person.previously %}Previous Member{% if person.role %}, {% endif %}{% endif %}{{ person.role }}</p>
      {% if person.funds %}
      <p class="person-funds">Funded by: {{ person.funds }}</p>
      {% elsif person.previously%}
      {% else %}
      <p class="person-funds">Funded by: SISSA</p>
      {% endif %}
      <p class="person-research">
        {% if person.previously %}<p>{{ person.previously | markdownify }}</p> {% endif %}
        {{ person.research | markdownify }}
      </p>
      <div class="person-links">
        {% if person.email %}
        <a href="mailto:{{ person.email }}" target="_blank" aria-label="Email" title="Email"><i class="fas fa-envelope"></i></a>
        {% endif %}
        {% if person.phone %}
        <a href="tel:{{ person.phone }}" target="_blank" aria-label="Phone" title="Phone"><i class="fas fa-phone"></i></a>
        {% endif %}
        {% if person.thesis %}
        <a href="{{ person.thesis }}" target="_blank" aria-label="PhD Thesis" title="PhD Thesis"><i class="fas fa-book"></i></a>
        {% endif %}
        {% if person.orcid %}
        <a href="https://orcid.org/{{ person.orcid }}" target="_blank" aria-label="ORCID" title="ORCID"><i class="fab fa-orcid"></i></a>
        {% endif %}
        {% if person.scholar %}
        <a href="{{ person.scholar }}" target="_blank" aria-label="Google Scholar" title="Google Scholar"><i class="fas fa-graduation-cap"></i></a>
        {% endif %}
        {% if person.prereview && person.orcid %}
        <a href="https://prereview.org/profiles/{{ person.orcid }}" target="_blank" aria-label="PREreview" title="PREreview"><i class="fas fa-clipboard"></i></a>
        {% endif %}
        {% if person.bluesky %}
        <a href="{{ person.bluesky }}" target="_blank" aria-label="Bluesky" title="Bluesky"><i class="fab fa-bluesky"></i></a>
        {% endif %}
        {% if person.twitter %}
        <a href="{{ person.twitter }}" target="_blank" aria-label="Twitter/X" title="Twitter/X"><i class="fab fa-x-twitter"></i></a>
        {% endif %}
        {% if person.linkedin %}
        <a href="{{ person.linkedin }}" target="_blank" aria-label="LinkedIn" title="LinkedIn"><i class="fab fa-linkedin"></i></a>
        {% endif %}
        {% if person.github %}
        <a href="{{ person.github }}" target="_blank" aria-label="GitHub" title="GitHub"><i class="fab fa-github"></i></a>
        {% endif %}
      </div>
    </div>
  </div>
  {% endfor %}
</div>

<script>
  function filterPeople(role) {
    const cards = document.querySelectorAll('.person-card');
    cards.forEach(card => {
        const roles = card.getAttribute('data-role');
        card.style.display = roles.includes(role) ? 'block' : 'none';
    });

    // Highlight the active tab
    const tabs = document.querySelectorAll('.tab-button');
    tabs.forEach(tab => {
        tab.classList.remove('active');
        if (tab.getAttribute('data-tab') === role) {
            tab.classList.add('active');
        }
    });
}

// Default tab on page load
document.addEventListener('DOMContentLoaded', () => {
    filterPeople('current');
});
</script>

<style>
.tabs-container {
  margin-top: 20px;
  text-align: center; /* Center the tabs */
}

.tab-button {
  background-color: white;
  border: 2px solid #1e6bb8; /* Blue border */
  color: #1e6bb8; /* Blue text */
  padding: 10px 20px;
  font-size: 16px;
  margin: 5px;
  border-radius: 5px; /* Rounded corners */
  cursor: pointer;
  transition: all 0.3s ease; /* Smooth hover effect */
  display: inline-block; /* Ensure buttons are inline */
}

.tab-button:hover {
  background-color: #1e6bb8; /* Blue background on hover */
  color: white; /* White text on hover */
}

.tab-button.active {
  background-color: #1e6bb8; /* Blue background for active state */
  color: white; /* White text for active state */
  border-color: #1e6bb8; /* Match the background color */
}

</style>


