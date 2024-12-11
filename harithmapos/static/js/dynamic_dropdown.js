function setupDynamicDropdown(inputId, dropdownId, searchUrl, hiddenId) {
    const inputElement = document.getElementById(inputId);
    const dropdownElement = document.getElementById(dropdownId);
    const hiddenElement = document.getElementById(hiddenId);

    // When user types in the input field
    inputElement.addEventListener("input", () => {
        const query = inputElement.value;

        // Clear the hidden element's value if the user starts typing
        hiddenElement.value = "";

        if (query.length > 0) {
            fetch(`${searchUrl}?q=${encodeURIComponent(query)}`)
                .then((response) => response.json())
                .then((data) => {
                    dropdownElement.innerHTML = "";

                    if (data.length > 0) {
                        data.forEach((item) => {
                            const listItem = document.createElement("li");
                            listItem.className = "dropdown-item";
                            // Display both ID and name/number
                            listItem.textContent = `${item.id} - ${item.number || item.name}`; 
                            listItem.dataset.id = item.id; // Store the ID as a data attribute

                            // When an item is clicked
                            listItem.addEventListener("click", () => {
                                inputElement.value = `${item.id} - ${item.number || item.name}`; // Show ID and name/number
                                hiddenElement.value = listItem.dataset.id; // Set hidden input's value to the ID
                                dropdownElement.innerHTML = ""; // Clear dropdown
                            });

                            dropdownElement.appendChild(listItem);
                        });
                        dropdownElement.classList.add("show");
                    } else {
                        dropdownElement.innerHTML = '<li class="dropdown-item text-muted">No results found</li>';
                        dropdownElement.classList.add("show");
                    }
                });
        } else {
            dropdownElement.classList.remove("show");
        }
    });

    // Close dropdown when clicking outside
    document.addEventListener("click", (event) => {
        if (!dropdownElement.contains(event.target) && event.target !== inputElement) {
            dropdownElement.classList.remove("show");
        }
    });
}