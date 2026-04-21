document.addEventListener('DOMContentLoaded', () => {
    const rollInput = document.getElementById('roll_number');
    const form = document.getElementById('registration-form');

    if (rollInput && form) {
        // Real-time roll number validation
        rollInput.addEventListener('input', (e) => {
            const val = e.target.value;
            // Only allow digits
            if (!/^\d*$/.test(val)) {
                e.target.value = val.replace(/\D/g, '');
            }

            const currentLength = e.target.value.length;
            const inputGroup = e.target.closest('.input-group');
            const errorMsgEl = document.getElementById('roll-error');

            if (currentLength > 0 && currentLength < 8) {
                inputGroup.classList.add('invalid');
                errorMsgEl.textContent = `Needs 8 digits. Currently ${currentLength}.`;
            } else if (currentLength === 8) {
                inputGroup.classList.remove('invalid');
                errorMsgEl.textContent = '';
            } else {
                inputGroup.classList.remove('invalid');
            }
        });

        // Form submission validation logic
        form.addEventListener('submit', (e) => {
            const rollVal = rollInput.value;
            if (rollVal.length !== 8) {
                e.preventDefault();
                const inputGroup = rollInput.closest('.input-group');
                inputGroup.classList.add('invalid');
                document.getElementById('roll-error').textContent = 'Please double check: must be exactly 8 digits.';
                
                // Add a shake animation class temporarily
                inputGroup.style.animation = 'shake 0.4s ease-in-out';
                setTimeout(() => {
                    inputGroup.style.animation = '';
                }, 400);
            }
        });
    }
});

// Helper shake animation via JS injection for bad submit
const style = document.createElement('style');
style.innerHTML = `
@keyframes shake {
    0%, 100% { transform: translateX(0); }
    25% { transform: translateX(-5px); }
    50% { transform: translateX(5px); }
    75% { transform: translateX(-5px); }
}
`;
document.head.appendChild(style);
