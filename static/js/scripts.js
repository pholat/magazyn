/**
 * scripts.js
 * Handles inline editing, Deletion, and Copy UID
 */

/* =========================================
   HELPER: COPY UID TO CLIPBOARD
   ========================================= */
function copyToClipboard(text, element) {
    if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(text).then(() => {
            showCopyFeedback(element);
        }).catch(err => {
            console.error('Failed to copy: ', err);
            fallbackCopy(text, element);
        });
    } else {
        fallbackCopy(text, element);
    }
}

function fallbackCopy(text, element) {
    // Fallback for older browsers / insecure contexts
    const textArea = document.createElement("textarea");
    textArea.value = text;
    document.body.appendChild(textArea);
    textArea.select();
    try {
        document.execCommand('copy');
        showCopyFeedback(element);
    } catch (err) {
        console.error('Fallback copy failed', err);
        alert("UID: " + text); // Last resort: show alert so user can copy manually
    }
    document.body.removeChild(textArea);
}

function showCopyFeedback(element) {
    const originalText = element.innerText;
    element.innerText = "Copied!";
    element.style.background = "#28a745"; // Green
    element.style.color = "white";
    
    setTimeout(() => {
        element.innerText = originalText;
        element.style.background = ""; // Reset
        element.style.color = "";
    }, 1500);
}

/* =========================================
   HELPER: SELECT2 DATA
   ========================================= */
function getSelect2Data() {
    if (!window.availableLocations) return [];
    return window.availableLocations.map(loc => ({ id: loc, text: loc }));
}

/* =========================================
   DELETE ITEM
   ========================================= */
function deleteItem(uid, btnElement) {
    if (!confirm("Are you sure you want to delete this item?")) return;

    fetch(`/items/${uid}`, { method: 'DELETE' })
    .then(response => {
        if (response.ok) {
            // Support both Table row and Mobile Card view
            const row = btnElement.closest('tr') || btnElement.closest('.card-mobile') || btnElement.parentElement.parentElement;
            if (row) {
                row.style.opacity = '0';
                setTimeout(() => row.remove(), 500);
            } else {
                location.reload();
            }
        } else {
            alert("Failed to delete.");
        }
    });
}

/* =========================================
   DASHBOARD LOCATION EDIT
   ========================================= */
function editDashboardLocation(td, uid) {
    // 1. Safety Checks
    if ($(td).find('select').length > 0 || $(td).find('input').length > 0) return;
    
    const currentText = td.innerText === "Set Location" ? "" : td.innerText.trim();

    // 2. Check if jQuery/Select2 is loaded. If not, fallback to text input.
    if (typeof $ === 'undefined' || !$.fn.select2) {
        console.warn("Select2 not loaded, falling back to simple input");
        const input = document.createElement("input");
        input.value = currentText;
        input.className = "edit-input";
        input.onblur = function() { saveSimple(this.value); };
        input.onkeydown = function(e) { if(e.key==="Enter") this.blur(); };
        td.innerHTML = "";
        td.appendChild(input);
        input.focus();
        
        function saveSimple(val) {
            td.innerText = val || "Set Location";
            updateLocationApi(uid, val);
        }
        return;
    }

    // 3. Create Select2 Logic
    const $select = $('<select>').css('width', '100%');
    if (currentText) $select.append(new Option(currentText, currentText, true, true));
    
    $(td).empty().append($select);

    $select.select2({
        tags: true,
        data: getSelect2Data(),
        width: '100%'
    });

    $select.select2('open');

    // 4. Save Logic
    function save() {
        // Delay to allow value capture
        setTimeout(() => {
            const newValue = $select.val();
            
            if ($select.data('select2')) {
                $select.select2('destroy');
            }
            td.innerText = newValue || "Set Location";

            if (newValue !== currentText) {
                updateLocationApi(uid, newValue);
            }
        }, 50);
    }

    $select.on('select2:close', save);
}

/* =========================================
   ITEM VIEW EDIT (Unified)
   ========================================= */
function editItemField(elementId, fieldType, uid) {
    const displayEl = document.getElementById(elementId);
    if (!displayEl) return;
    if (displayEl.querySelector('input, textarea, select')) return;

    let currentText = displayEl.innerText.trim();
    if (["Click to add note...", "Set Location", "None"].includes(currentText)) currentText = "";

    // --- NOTES ---
    if (fieldType === 'note') {
        const textarea = document.createElement("textarea");
        textarea.className = "edit-input";
        textarea.style.height = "100px";
        textarea.value = currentText;
        displayEl.innerHTML = "";
        displayEl.appendChild(textarea);
        textarea.focus();
        
        textarea.onblur = () => {
            const val = textarea.value.trim();
            displayEl.innerText = val || "Click to add note...";
            updateNoteApi(uid, val);
        };
        return;
    }

    // --- DATE ---
    if (fieldType === 'date') {
        const input = document.createElement("input");
        input.type = "datetime-local";
        input.className = "edit-input";
        if (currentText.length >= 16) input.value = currentText.substring(0, 16).replace(" ", "T");
        
        displayEl.innerHTML = "";
        displayEl.appendChild(input);
        input.focus();
        
        const saveDate = () => {
            const val = input.value;
            if(!val) { displayEl.innerText = currentText; return; }
            displayEl.innerText = val.replace("T", " ") + ":00";
            updateDateApi(uid, val);
        };
        input.onblur = saveDate;
        input.onkeydown = (e) => { if(e.key==="Enter") saveDate(); };
        return;
    }

    // --- LOCATION (Select2) ---
    // Reuse the dashboard logic but applied to a specific ID
    // Check for Select2 support first
    if (typeof $ === 'undefined' || !$.fn.select2) {
        alert("Select2 library missing. Please refresh.");
        return;
    }

    const $displayEl = $(displayEl);
    const $select = $('<select>');
    if (currentText) $select.append(new Option(currentText, currentText, true, true));

    $displayEl.empty().append($select);
    $select.select2({ tags: true, data: getSelect2Data(), width: '100%' });
    $select.select2('open');

    const saveLoc = () => {
        setTimeout(() => {
            const val = $select.val();
            if ($select.data('select2')) $select.select2('destroy');
            displayEl.innerText = val || "Set Location";
            if (val !== currentText) updateLocationApi(uid, val);
        }, 50);
    };
    $select.on('select2:close', saveLoc);
}

/* =========================================
   API HELPERS
   ========================================= */
function updateLocationApi(uid, val) {
    fetch(`/items/${uid}/location`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ location: val })
    }).then(res => {
        if(res.ok && val && window.availableLocations && !window.availableLocations.includes(val)) {
            window.availableLocations.push(val);
        }
    });
}

function updateNoteApi(uid, val) {
    fetch(`/items/${uid}/note`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ note: val })
    });
}

function updateDateApi(uid, val) {
    fetch(`/items/${uid}/date`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ date: val })
    });
}
