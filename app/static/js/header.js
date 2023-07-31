document.addEventListener("DOMContentLoaded", () => {
  const advSearchToggle = document.getElementById("adv-search-toggle");
  const advSearchDiv = document.getElementById("adv-search-div");
  const searchBar = document.getElementById("search-bar");
  const countrySelect = document.getElementById("result-country");
  const timePeriodSelect = document.getElementById("result-time-period");
  const arrowKeys = [37, 38, 39, 40];
  let searchValue = searchBar.value;

  const tackOnParams = (url) => {
    const params = new URLSearchParams();
    if (timePeriodSelect.value !== "") {
      params.append("tbs", timePeriodSelect.value);
    }
    if (countrySelect.value !== "") {
      params.append("country", countrySelect.value);
    }
    return `${url}?${params.toString()}`;
  };

  const handleSelectionChange = () => {
    const str = window.location.href;
    const n = str.lastIndexOf("/search");
    if (n > 0) {
      const newURL = tackOnParams(str.substring(0, n));
      window.location.href = newURL;
    }
  };

  countrySelect.addEventListener("change", handleSelectionChange);
  timePeriodSelect.addEventListener("change", handleSelectionChange);

  const toggleAdvancedSearch = (on) => {
    advSearchDiv.style.maxHeight = on ? "90px" : "0px";
    advSearchToggle.checked = on;
  };

  toggleAdvancedSearch(advSearchToggle.checked);

  advSearchToggle.addEventListener("click", () => {
    toggleAdvancedSearch(advSearchToggle.checked);
  });

  const handleUserInput = () => {
    // Perform actions related to user input here
  };

  searchBar.addEventListener("keyup", (event) => {
    if (event.keyCode === 13) {
      document.getElementById("search-form").submit();
    } else if (searchBar.value !== searchValue && !arrowKeys.includes(event.keyCode)) {
      searchValue = searchBar.value;
      handleUserInput();
    }
  });
});
