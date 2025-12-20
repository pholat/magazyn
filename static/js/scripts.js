/**
 * scripts.js
 * Handles inline editing, Deletion, and Copy UID
 */

/* =========================================
   HELPER: COPY UID
   ========================================= */
function copyToClipboard(text, element) {
    if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(text).then(() => showCopyFeedback(element))
        .catch(err => fallbackCopy(text, element));
    } else {
        fallbackCopy(text, element);
    }
}

function fallbackCopy(text, element) {
    const textArea = document.createElement("textarea");
    textArea.value = text;
    document.body.appendChild(textArea);
    textArea.select();
    try { document.execCommand('copy'); showCopyFeedback(element); } 
    catch (err) { alert("UID: " + text); }
    document.body.removeChild(textArea);
}

function showCopyFeedback(element) {
    const originalText = element.innerText;
    element.innerText = "Copied!";
    element.style.background = "#28a745"; element.style.color = "white";
    setTimeout(() => { element.innerText = originalText; element.style.background = ""; element.style.color = ""; }, 1500);
}

/* =========================================
   HELPER: SELECT2 DATA GENERATOR
   ========================================= */
function getSelect2Data(sourceArray) {
    if (!sourceArray) return [];
    return sourceArray.map(item => ({ id: item, text: item }));
}

/* =========================================
   DELETE ITEM
   ========================================= */
function deleteItem(uid, btnElement) {
    if (!confirm("Are you sure you want to delete this item?")) return;
    fetch(`/items/${uid}`, { method: 'DELETE' }).then(response => {
        if (response.ok) {
            const row = btnElement.closest('tr') || btnElement.closest('.card-mobile') || btnElement.parentElement.parentElement;
            if (row) { row.style.opacity = '0'; setTimeout(() => row.remove(), 500); } 
            else location.reload();
        } else { alert("Failed to delete."); }
    });
}

/* =========================================
   DASHBOARD: LOCATION EDIT
   ========================================= */
function editDashboardLocation(td, uid) {
    if ($(td).find('select, input').length > 0) return;
    
    const currentText = td.innerText === "Set Location" ? "" : td.innerText.trim();

    if (typeof $ === 'undefined' || !$.fn.select2) return; // Safety check

    const $select = $('<select>').css('width', '100%');
    if (currentText) $select.append(new Option(currentText, currentText, true, true));
    
    $(td).empty().append($select);

    $select.select2({
        tags: true,
        data: getSelect2Data(window.availableLocations),
        width: '100%'
    });

    $select.select2('open');

    function save() {
        setTimeout(() => {
            const newValue = $select.val();
            if ($select.data('select2')) $select.select2('destroy');
            td.innerText = newValue || "Set Location";

            if (newValue !== currentText) {
                updateApi(uid, 'location', { location: newValue });
            }
        }, 50);
    }
    $select.on('select2:close', save);
}

/* =========================================
   DASHBOARD: TAGS EDIT (NEW)
   ========================================= */
function editDashboardTags(td, uid) {
    if ($(td).find('select').length > 0) return;

    // Read from data attribute for reliability (avoids parsing HTML pills)
    const rawTags = td.getAttribute('data-current-tags') || "";
    const currentTags = rawTags ? rawTags.split(',') : [];

    const $select = $('<select multiple="multiple">').css('width', '100%');
    
    // Pre-select existing tags
    currentTags.forEach(tag => {
        if(tag) $select.append(new Option(tag, tag, true, true));
    });

    $(td).empty().append($select);

    $select.select2({
        tags: true,
        tokenSeparators: [',', ' '],
        data: getSelect2Data(window.availableTags),
        width: '100%'
    });

    $select.select2('open');

    function save() {
        setTimeout(() => {
            const newTags = $select.val() || [];
            if ($select.data('select2')) $select.select2('destroy');

            // 1. Update Data Attribute
            const newTagsStr = newTags.join(',');
            td.setAttribute('data-current-tags', newTagsStr);

            // 2. Render Pills HTML
            if (newTags.length > 0) {
                td.innerHTML = newTags.map(t => `<span class="tag-pill">${t}</span>`).join('');
            } else {
                td.innerHTML = '<span style="color:#ccc; font-size:0.8em;">Add tags...</span>';
            }

            // 3. API Call
            if (newTagsStr !== rawTags) {
                updateApi(uid, 'tags', { tags: newTags });
                // Add new tags to global pool
                newTags.forEach(t => {
                    if(window.availableTags && !window.availableTags.includes(t)) window.availableTags.push(t);
                });
            }
        }, 50);
    }
    $select.on('select2:close', save);
}

/* =========================================
   ITEM DETAIL VIEW EDIT
   ========================================= */
function editItemField(elementId, fieldType, uid) {
    const displayEl = document.getElementById(elementId);
    if (!displayEl || displayEl.querySelector('input, textarea, select')) return;

    let currentText = displayEl.innerText.trim();
    if (["Click to add note...", "Set Location", "Click to add tags..."].includes(currentText)) currentText = "";

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
            updateApi(uid, 'note', { note: val });
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
            displayEl.innerText = val ? val.replace("T", " ") + ":00" : currentText;
            if(val) updateApi(uid, 'date', { date: val });
        };
        input.onblur = saveDate;
        input.onkeydown = (e) => { if(e.key==="Enter") input.blur(); };
        return;
    }

    // --- TAGS (Multi Select) ---
    if (fieldType === 'tags') {
        const $displayEl = $(displayEl);
        const $select = $('<select multiple="multiple">');
        if (currentText) {
            currentText.split(',').map(t=>t.trim()).forEach(tag => {
                if(tag) $select.append(new Option(tag, tag, true, true));
            });
        }
        $displayEl.empty().append($select);
        $select.select2({ tags: true, tokenSeparators: [',', ' '], data: getSelect2Data(window.availableTags), width: '100%' });
        $select.select2('open');
        
        const saveTags = () => {
            setTimeout(() => {
                const newTags = $select.val() || [];
                if ($select.data('select2')) $select.select2('destroy');
                displayEl.innerText = newTags.join(", ") || "Click to add tags...";
                updateApi(uid, 'tags', { tags: newTags });
            }, 50);
        };
        $select.on('select2:close', saveTags);
        return;
    }

    // --- LOCATION (Select2) ---
    const $displayEl = $(displayEl);
    const $select = $('<select>');
    if (currentText) $select.append(new Option(currentText, currentText, true, true));
    $displayEl.empty().append($select);
    $select.select2({ tags: true, data: getSelect2Data(window.availableLocations), width: '100%' });
    $select.select2('open');

    const saveLoc = () => {
        setTimeout(() => {
            const val = $select.val();
            if ($select.data('select2')) $select.select2('destroy');
            displayEl.innerText = val || "Set Location";
            if (val !== currentText) updateApi(uid, 'location', { location: val });
        }, 50);
    };
    $select.on('select2:close', saveLoc);
}

/* =========================================
   API HELPER
   ========================================= */
function updateApi(uid, endpoint, data) {
    fetch(`/items/${uid}/${endpoint}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
    }).then(res => {
        if(res.ok && endpoint === 'location' && data.location && window.availableLocations && !window.availableLocations.includes(data.location)) {
            window.availableLocations.push(data.location);
        }
    });
}
