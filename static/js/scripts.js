/**
 * scripts.js
 * Handles inline editing with Select2 and Textareas
 */

function getSelect2Data() {
    if (!window.availableLocations) return [];
    // Convert array of strings to Select2 format {id, text}
    return window.availableLocations.map(loc => ({ id: loc, text: loc }));
}

/* =========================================
   DASHBOARD LOGIC
   ========================================= */

function editDashboardLocation(td, uid) {
    if ($(td).find('select').length > 0) return;

    const currentText = td.innerText === "Set Location" ? "" : td.innerText.trim();
    
    // Create Select Element
    const $select = $('<select>').css('width', '100%');
    
    // If current value exists, add it as an option so it shows up selected
    if (currentText) {
        $select.append(new Option(currentText, currentText, true, true));
    }

    $(td).empty().append($select);

    // Init Select2
    $select.select2({
        tags: true,
        data: getSelect2Data(),
        width: '100%'
    });

    $select.select2('open');

    function save() {
        // Timeout ensures Select2 has fully processed the value change
        setTimeout(() => {
            const newValue = $select.val();
            $select.select2('destroy');
            td.innerText = newValue || "Set Location";

            if (newValue === currentText && newValue !== "") return;

            // API Call
            fetch(`/items/${uid}/location`, {
                method: 'PATCH',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ location: newValue })
            }).then(response => {
                if (!response.ok) {
                    td.innerText = currentText;
                    alert("Failed to save.");
                } else {
                    // Update global list if new tag
                    if (newValue && !window.availableLocations.includes(newValue)) {
                        window.availableLocations.push(newValue);
                    }
                }
            });
        }, 50);
    }

    $select.on('select2:close', save);
}


/* =========================================
   ITEM DETAIL VIEW LOGIC
   ========================================= */

function editItemField(elementId, fieldType, uid) {
    const displayEl = document.getElementById(elementId);
    if ($(displayEl).find('input, textarea, select').length > 0) return;

    const currentText = (displayEl.innerText === "Click to add note..." || displayEl.innerText === "Set Location") 
                        ? "" 
                        : displayEl.innerText.trim();

    // --- HANDLE NOTES ---
    if (fieldType === 'note') {
        const textarea = document.createElement("textarea");
        textarea.className = "edit-input";
        textarea.style.height = "100px";
        textarea.value = currentText;
        displayEl.innerHTML = "";
        displayEl.appendChild(textarea);
        textarea.focus();

        const saveNote = () => {
            const newValue = textarea.value.trim();
            displayEl.innerText = newValue || "Click to add note...";
            fetch(`/items/${uid}/note`, {
                method: 'PATCH',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ note: newValue })
            });
        };
        textarea.addEventListener("blur", saveNote);
        textarea.addEventListener("keydown", (e) => {
            if ((e.ctrlKey || e.metaKey) && e.key === "Enter") saveNote();
        });
        return;
    }

    // --- HANDLE LOCATION (Select2) ---
    const $displayEl = $(displayEl);
    const $select = $('<select>');
    
    if (currentText) {
        $select.append(new Option(currentText, currentText, true, true));
    }

    $displayEl.empty().append($select);

    $select.select2({
        tags: true,
        data: getSelect2Data(),
        width: '100%'
    });

    $select.select2('open');

    const saveLocation = () => {
        setTimeout(() => {
            const newValue = $select.val();
            $select.select2('destroy');
            displayEl.innerText = newValue || "Set Location";

            if (newValue === currentText && newValue !== "") return;

            fetch(`/items/${uid}/location`, {
                method: 'PATCH',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ location: newValue })
            }).then(res => {
                if(res.ok && newValue && !window.availableLocations.includes(newValue)) {
                    window.availableLocations.push(newValue);
                }
            });
        }, 50);
    };

    $select.on('select2:close', saveLocation);
}
