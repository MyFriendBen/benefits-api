// Safe table sorting (no crash if no .table)
function initializeTableSorting() {
  let table = document.querySelector(".table");
  if (!table) return;
  let headers = table.querySelectorAll("th");
  if (!headers || headers.length === 0) return;
  let currentSortColumn = null;
  let sortDirection = "asc";

  headers.forEach(function (header, index) {
    header.addEventListener("click", function () { 
      sortTable(index); 
    });
  });

  function sortTable(columnIndex) {
    let rows = Array.from(table.querySelectorAll("tbody tr"));
    if (columnIndex === currentSortColumn) {
      sortDirection = sortDirection === "asc" ? "desc" : "asc";
    } else {
      currentSortColumn = columnIndex;
      sortDirection = "asc";
    }

    rows.sort(function (a, b) {
      let cellA = a.querySelectorAll("td")[columnIndex].textContent.trim();
      let cellB = b.querySelectorAll("td")[columnIndex].textContent.trim();

      let valueA = isNaN(cellA) ? cellA.toLowerCase() : parseInt(cellA, 10);
      let valueB = isNaN(cellB) ? cellB.toLowerCase() : parseInt(cellB, 10);

      if (valueA < valueB) return sortDirection === "asc" ? -1 : 1;
      if (valueA > valueB) return sortDirection === "asc" ? 1 : -1;
      return 0;
    });

    let tbody = table.querySelector("tbody");
    rows.forEach(function (row) {
      tbody.appendChild(row);
    });
  }
}

// For handling the sidebar menu
function initializeSidebarMenu() {
  let menuItems = document.querySelectorAll(".menu-list .sidebar-item");
  let currentUrl = window.location.href;

  menuItems.forEach(function (menuItem) {
    let linkUrl = menuItem.href;

    if (linkUrl === currentUrl) {
      menuItem.classList.add("is-active");
    }

    menuItem.addEventListener("click", function (event) {
      menuItems.forEach(function (item) {
        item.classList.remove("is-active");
      });

      event.currentTarget.classList.add("is-active");
    });
  });
}

// For handling the dropdown menu in the tables
function initializeDropdowns() {
  let dropdowns = document.querySelectorAll(".dropdown");
  dropdowns.forEach(function (dropdown) {
    let dropdownButton = dropdown.querySelector(".button");
    let dropdownSpan = dropdown.querySelector(".material-symbols-outlined");
    let dropdownContent = dropdown.querySelector(".dropdown-content");
    if (!dropdownButton) return;

    dropdownButton.addEventListener("click", function (event) {
      event.preventDefault();
      dropdown.classList.toggle("is-active");
      if (dropdown.classList.contains("is-active")) {
        if (dropdownSpan) dropdownSpan.textContent = "expand_less";
        checkDropdownPosition(dropdown, dropdownContent);
      } else {
        if (dropdownSpan) dropdownSpan.textContent = "expand_more";
        dropdown.classList.remove("is-top");
      }
    });

    // Close the dropdown if the user clicks outside of it
    document.addEventListener("click", function (event) {
      let isClickInside = dropdown.contains(event.target);
      if (!isClickInside) {
        dropdown.classList.remove("is-active");
        dropdown.classList.remove("is-top");
        if (dropdownSpan) dropdownSpan.textContent = "expand_more";
      }
    });

    // Close dropdowns when the page is scrolled
    window.addEventListener("scroll", function () {
      dropdown.classList.remove("is-active");
      dropdown.classList.remove("is-top");
      if (dropdownSpan) dropdownSpan.textContent = "expand_more";
    });
  });
}

function checkDropdownPosition(dropdown, dropdownContent) {
  if (!dropdownContent) return;
  let dropdownRect = dropdown.getBoundingClientRect();
  let dropdownContentRect = dropdownContent.getBoundingClientRect();
  let viewportHeight = window.innerHeight;

  if (dropdownRect.bottom + dropdownContentRect.height > viewportHeight) {
    dropdown.classList.remove("is-top");
  } else {
    dropdown.classList.add("is-top");
  }
}

// Convert UTC ISO in data-utc-date to browser timezone
function formatDates() {  
  const els = document.querySelectorAll(".utc-date");  
  
  if (els.length === 0) {
    return;
  }
  
  els.forEach(function (el, index) {
    const iso = el.getAttribute("data-utc-date");    
    
    if (!iso || iso === "Never") {
      return;
    }
    
    try {
      const d = new Date(iso);
      if (isNaN(d.getTime())) {
        return;
      }
      
      const formatted = new Intl.DateTimeFormat(navigator.language, {
        year: "numeric", 
        month: "short", 
        day: "numeric",
        hour: "numeric", 
        minute: "numeric", 
        hour12: true, 
        timeZoneName: "short"
      }).format(d);
      
      el.textContent = formatted;
    } catch (e) {
      console.error("Error formatting date:", e);
    }
  });
}
window.formatDates = formatDates;

function initializeAll() {  
  try { initializeTableSorting(); } catch (e) { console.warn("initializeTableSorting error:", e); }
  try { initializeSidebarMenu(); } catch (e) { console.warn("initializeSidebarMenu error:", e); }
  try { initializeDropdowns(); } catch (e) { console.warn("initializeDropdowns error:", e); }
  formatDates();
}

document.addEventListener("DOMContentLoaded", initializeAll);
document.body.addEventListener("htmx:afterSwap", function() {
  console.log("HTMX content swapped - calling formatDates");
  setTimeout(formatDates, 0);
});