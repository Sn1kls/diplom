document.addEventListener('DOMContentLoaded', function () {
    const contentTypeSelect = document.querySelector('#id_content_type');
    const descriptionInput = document.getElementById('id_description');

    if (!contentTypeSelect) return;

    const fields = {
        'video': ['.field-video_url'],
        'audio': ['.field-audio_url'],
        'text': ['.field-text_content'],
        'quiz': ['.field-quiz_fk'],
        'homework': ['#homeworks-group']
    };

    const allSelectors = Object.values(fields).flat().join(', ');

    function toggleFields() {
        const selectedValue = contentTypeSelect.value;

        document.querySelectorAll(allSelectors).forEach(el => {
            el.style.setProperty('display', 'none', 'important');
        });

        if (descriptionInput) {
            const descriptionRow = descriptionInput.closest('.form-row') || descriptionInput.closest('.field-description') || descriptionInput.closest('.mb-6');
            if (descriptionRow) {
                if (['video', 'audio'].includes(selectedValue)) {
                    descriptionRow.style.display = 'block';
                } else {
                    descriptionRow.style.setProperty('display', 'none', 'important');
                }
            }
        }

        if (fields[selectedValue]) {
            fields[selectedValue].forEach(selector => {
                const el = document.querySelector(selector);
                if (el) {
                    el.style.display = 'block';
                }
            });
        }
    }

    contentTypeSelect.addEventListener('change', toggleFields);
    toggleFields();
});