document.addEventListener('DOMContentLoaded', function() {
    const typeSelect = document.querySelector('#id_question_type');
    const tabsGroup = document.querySelector('#tabs-wrapper');
    const incorrectAnswerSelect = document.querySelector('.field-incorrect_answer')

    function toggleInlines() {
        if (typeSelect.value === 'text') {
            tabsGroup.style.display = 'none';
            incorrectAnswerSelect.style.display = 'none';
        } else {
            tabsGroup.style.display = 'block';
            incorrectAnswerSelect.style.display = 'block';
        }
    }

    typeSelect.addEventListener('change', toggleInlines);
    toggleInlines();
});
