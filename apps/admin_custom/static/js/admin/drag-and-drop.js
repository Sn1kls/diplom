document.addEventListener('DOMContentLoaded', function () {
    let dragSrcEl = null;
    const storage_message_key = 'show_success_change_order_msg'

    const pendingMessage = localStorage.getItem(storage_message_key);
    if (pendingMessage) {
        showSuccessMessage(pendingMessage);
        localStorage.removeItem(storage_message_key);
    }


    function initNativeDnD() {
        const tables = document.querySelectorAll('table');

        tables.forEach(table => {
            const rows = table.querySelectorAll('tbody');
            const hasOrder = table.querySelector('.field-order, .column-order');
            if (!hasOrder) return;

            rows.forEach(row => {
                const orderCell = row.querySelector('.field-order, .column-order');
                if (!orderCell) return;

                row.setAttribute('draggable', 'true');
                row.style.cursor = 'move';

                if (!orderCell.querySelector('.drag-handle')) {
                    const input = orderCell.querySelector('input');
                    if (input) input.style.display = 'none';

                    orderCell.insertAdjacentHTML('beforeend', '<span class="drag-handle" style="cursor:grab; font-size:20px; color:#9ca3af; user-select:none;">⠿</span>');
                }

                if (!row.dataset.dragInitialized) {
                    row.addEventListener('dragstart', handleDragStart, false);
                    row.addEventListener('dragenter', handleDragEnter, false);
                    row.addEventListener('dragover', handleDragOver, false);
                    row.addEventListener('dragleave', handleDragLeave, false);
                    row.addEventListener('drop', handleDrop, false);
                    row.addEventListener('dragend', handleDragEnd, false);
                    row.dataset.dragInitialized = "true";
                }
            });
        });
    }

    function handleDragStart(e) {
        dragSrcEl = this;
        e.dataTransfer.effectAllowed = 'move';

        e.dataTransfer.setData('text/html', this.innerHTML);
        this.classList.add('drag-active');
    }

    function handleDragOver(e) {
        if (e.preventDefault) e.preventDefault();
        e.dataTransfer.dropEffect = 'move';
        return false;
    }

    function handleDragEnter(e) {
        this.classList.add('over');
    }

    function handleDragLeave(e) {
        this.classList.remove('over');
    }

    function handleDrop(e) {
        if (e.stopPropagation) e.stopPropagation();

        if (dragSrcEl !== this) {
            const allRows = Array.from(this.parentNode.children);
            const dragIdx = allRows.indexOf(dragSrcEl);
            const dropIdx = allRows.indexOf(this);

            if (dragIdx < dropIdx) {
                this.parentNode.insertBefore(dragSrcEl, this.nextSibling);
            } else {
                this.parentNode.insertBefore(dragSrcEl, this);
            }
            saveNewOrder();
        }
        return false;
    }

    function handleDragEnd(e) {
        const rows = document.querySelectorAll('#result_list tbody');
        rows.forEach(row => {
            row.classList.remove('over');
            row.classList.remove('drag-active');
        });
    }

    function renderMessage(message, _type = "success") {
        const isError = _type === "error"
        const existingMessage = document.getElementById('order-saving-status-message');
        if (existingMessage) existingMessage.remove();

        const contentContainer = document.querySelector('#content-main');

        if (!contentContainer) {
            alert(message);
            return;
        }

        const messageElement = document.createElement('div');
        messageElement.id = 'order-saving-status-message';

        const baseClasses = [
            'mb-3',
            'px-3',
            'py-2.5',
            'leading-[18px]',
            'rounded-default',
            'animate-in',
            'slide-in-from-top-full',
            'fade-in',
            'duration-700',
            'ease-out'
        ];

        if (isError) {
            messageElement.classList.add(
                ...baseClasses,
                'bg-red-100',
                'text-red-700',
                'dark:bg-red-500/20',
                'dark:text-red-400'
            );
        } else {
            messageElement.classList.add(
                ...baseClasses,
                'bg-green-100',
                'text-green-700',
                'dark:bg-green-500/20',
                'dark:text-green-400'
            );
        }

        messageElement.innerHTML = `
        <div class="flex items-center">
            <div class="flex-shrink-0 mr-3">
                ${isError ? getErrorIcon() : getSuccessIcon()}
            </div>
            <div>${message}</div>
            <button onclick="this.closest('#order-saving-status-message').remove()" class="ml-auto pl-3 text-current opacity-70 cursor-pointer hover:opacity-100">
                ✕
            </button>
        </div>
    `;

        contentContainer.prepend(messageElement);

        setTimeout(() => {
            if (messageElement && messageElement.parentNode) {
                messageElement.remove();
            }
        }, 5000);
    }

    function showSuccessMessage(message) {
        return renderMessage(message, "success")
    }

    function showErrorMessage(message) {
        return renderMessage(message, "error")
    }

    function getSuccessIcon() {
        return `<svg class="h-5 w-5" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
        <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd" />
    </svg>`;
    }

    function getErrorIcon() {
        return `<svg class="h-5 w-5" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
        <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd" />
    </svg>`;
    }

    const getDjangoData = (id) => {
        const element = document.getElementById(id);
        return element ? JSON.parse(element.textContent) : null;
    };

    function saveNewOrder() {
        const rows = document.querySelectorAll('#result_list tbody tr, .inline-related tbody tr');
        let appLabel = getDjangoData('app-label-data');
        let modelName = getDjangoData('model-name-data');
        const data = [];

        // Check if we are dealing with an inline
        if (dragSrcEl) {
            // Find closest group container. Unfold might use id ending in -group but not class .inline-group
            const inlineGroup = dragSrcEl.closest('.inline-group, [id$="-group"]');

            if (inlineGroup) {
                const id = inlineGroup.id; // e.g., "answers-group"
                let prefix = '';

                if (id) {
                    // Extract prefix (e.g., "answers" from "answers-group")
                    prefix = id.replace(/-group$/, '');

                    const inlineConfig = {
                        "answers": {
                            "app_label": "quizzes",
                            "model_name": "Answer"
                        }
                    };

                    if (inlineConfig[prefix]) {
                        appLabel = inlineConfig[prefix].app_label;
                        modelName = inlineConfig[prefix].model_name;
                    }
                }

                // Limit rows to this inline group, handle potential absence of tbody
                const inlineRows = inlineGroup.querySelectorAll('tr:not(.empty-form)');
                // Deduplicate by id (some inlines render multiple TRs per object)
                const seenInline = new Set();
                const uniqueInlineIds = [];
                inlineRows.forEach(row => {
                    const idInput = row.querySelector('input[name$="-id"]');
                    if (idInput && idInput.value && !seenInline.has(idInput.value)) {
                        seenInline.add(idInput.value);
                        uniqueInlineIds.push(idInput.value);
                    }
                });
                // send 1-based sequential orders
                uniqueInlineIds.forEach((idVal, idx) => {
                    data.push({ id: idVal, order: idx});
                });
            } else {
                // Standard change list fallback
                // Use the table of the dragged element to scope the rows
                const parentTable = dragSrcEl.closest('table');
                if (parentTable) {
                    const standardRows = parentTable.querySelectorAll('tbody tr');
                    const seenStd = new Set();
                    const uniqueStdIds = [];
                    standardRows.forEach(row => {
                        const idInput = row.querySelector('.action-checkbox input, input[name$="-id"]');
                        if (idInput && idInput.value && !seenStd.has(idInput.value)) {
                            seenStd.add(idInput.value);
                            uniqueStdIds.push(idInput.value);
                        }
                    });
                    uniqueStdIds.forEach((idVal, idx) => data.push({ id: idVal, order: idx}));
                } else {
                    // Fallback to result_list if table structure is weird
                    const standardRows = document.querySelectorAll('#result_list tbody tr');
                    const seenResult = new Set();
                    const uniqueResultIds = [];
                    standardRows.forEach(row => {
                        const idInput = row.querySelector('.action-checkbox input, input[name$="-id"]');
                        if (idInput && idInput.value && !seenResult.has(idInput.value)) {
                            seenResult.add(idInput.value);
                            uniqueResultIds.push(idInput.value);
                        }
                    });
                    uniqueResultIds.forEach((idVal, idx) => data.push({ id: idVal, order: idx}));
                }
            }
        }


        if (data.length > 0) {
            fetch('/api/admin/save-order', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value,
                },
                body: JSON.stringify({
                    app_label: appLabel,
                    model_name: modelName,
                    orders: data
                })
            })
                .then(response => response.json())
                .then(res => {
                    window.location.reload();
                    localStorage.setItem(storage_message_key, `Order for ${modelName} saved successfully`);
                })
                .catch(err => showErrorMessage(`Error: failed to save ${modelName}`));
        }
    }

    initNativeDnD();

    const observer = new MutationObserver(initNativeDnD);
    const target = document.querySelector('table');
    if (target) observer.observe(target, { childList: true, subtree: true });
});