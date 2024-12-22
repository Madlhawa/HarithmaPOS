function setupDynamicDropdown(inputId, dropdownId, searchUrl, hiddenId, showAll = false) {
    const inputElement = document.getElementById(inputId);
    const dropdownElement = document.getElementById(dropdownId);
    const hiddenElement = document.getElementById(hiddenId);
    let selectedIndex = -1; // Keep track of the selected dropdown item index
    let isItemSelected = false; // Track if an item has been selected
    let debounceTimer = null; // Track the debounce timer

    // Fetch and display dropdown items
    const fetchDropdownItems = (query) => {
        fetch(`${searchUrl}?q=${encodeURIComponent(query)}`)
            .then((response) => response.json())
            .then((data) => {
                dropdownElement.innerHTML = "";
                selectedIndex = -1; // Reset selected index
                dropdownElement.classList.remove("show"); // Hide dropdown if no results

                if (data.length > 0) {
                    data.forEach((item, index) => {
                        const listItem = document.createElement("li");
                        listItem.className = "dropdown-item";

                        // Conditionally include price for "itemSearch"
                        if (inputId === "itemSearch") {
                            listItem.textContent = `${item.id} : ${item.number || item.name} ---------- ${item.price}`;
                        } else {
                            listItem.textContent = `${item.id} : ${item.number || item.name}`;
                        }

                        listItem.dataset.id = item.id; // Store the ID as a data attribute
                        listItem.addEventListener("click", () => {
                            inputElement.value = `${item.id} - ${item.number || item.name}`; // Show ID and name/number
                            hiddenElement.value = listItem.dataset.id; // Set hidden input's value to the ID
                            dropdownElement.innerHTML = ""; // Clear dropdown
                            dropdownElement.classList.remove("show"); // Hide dropdown after selection
                            isItemSelected = true; // Mark item as selected
                        });

                        // Set highlight for the selected item (based on the index)
                        if (index === selectedIndex) {
                            listItem.classList.add("active");
                        }

                        dropdownElement.appendChild(listItem);
                    });
                    dropdownElement.classList.add("show"); // Show dropdown if results are found
                } else {
                    dropdownElement.innerHTML = '<li class="dropdown-item text-muted">No results found</li>';
                    dropdownElement.classList.add("show"); // Show dropdown if no results found
                }
            });
    };

    // When user types in the input field
    inputElement.addEventListener("input", () => {
        if (isItemSelected) {
            return; // Stop searching if an item has already been selected
        }

        const query = inputElement.value;

        // Clear the hidden element's value if the user starts typing
        hiddenElement.value = "";

        // If a timer already exists, clear it before setting a new one
        clearTimeout(debounceTimer);

        // Set a new timer to delay the search request
        debounceTimer = setTimeout(() => {
            if (query.length > 0 || showAll) {
                fetchDropdownItems(query);
            } else {
                dropdownElement.classList.remove("show"); // Hide dropdown if input is empty
            }
        }, 300); // Adjust the delay time (in milliseconds) as needed
    });

    // Show all items when the input is focused if showAll is true
    inputElement.addEventListener("focus", () => {
        if (showAll && !isItemSelected) {
            fetchDropdownItems(""); // Fetch all items with an empty query
        }
    });

    // Handle keyboard navigation (Up/Down arrows, Enter, Tab)
    inputElement.addEventListener("keydown", (event) => {
        const listItems = dropdownElement.getElementsByClassName("dropdown-item");

        if (event.key === "ArrowDown") {
            // Move down the list
            if (selectedIndex < listItems.length - 1) {
                selectedIndex++;
            }
        } else if (event.key === "ArrowUp") {
            // Move up the list
            if (selectedIndex > 0) {
                selectedIndex--;
            }
        } else if (event.key === "Enter" && selectedIndex >= 0 && selectedIndex < listItems.length) {
            // Select the highlighted item when Enter is pressed
            const selectedItem = listItems[selectedIndex];
            inputElement.value = selectedItem.textContent; // Set input field to the selected item's text
            hiddenElement.value = selectedItem.dataset.id; // Set the hidden input field with the selected ID
            dropdownElement.innerHTML = ""; // Clear the dropdown
            dropdownElement.classList.remove("show"); // Hide the dropdown
            isItemSelected = true; // Mark item as selected
            event.preventDefault(); // Prevent form submission
        } else if (event.key === "Tab" && selectedIndex >= 0 && selectedIndex < listItems.length) {
            // Select the highlighted item when Tab is pressed
            const selectedItem = listItems[selectedIndex];
            inputElement.value = selectedItem.textContent; // Set input field to the selected item's text
            hiddenElement.value = selectedItem.dataset.id; // Set the hidden input field with the selected ID
            dropdownElement.innerHTML = ""; // Clear the dropdown
            dropdownElement.classList.remove("show"); // Hide the dropdown
            isItemSelected = true; // Mark item as selected
        }

        // Highlight the selected item in the dropdown
        Array.from(listItems).forEach((item, index) => {
            if (index === selectedIndex) {
                item.classList.add("active");
            } else {
                item.classList.remove("active");
            }
        });
    });

    // Close dropdown when clicking outside
    document.addEventListener("click", (event) => {
        if (!dropdownElement.contains(event.target) && event.target !== inputElement) {
            dropdownElement.classList.remove("show"); // Hide dropdown when clicking outside
        }
    });
}