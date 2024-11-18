document.addEventListener("DOMContentLoaded", function() {
    if (document.querySelector('.congratulations')) {
        let confettiContainer = document.querySelector('.confetti');
        for (let i = 0; i < 100; i++) {
            let confettiPiece = document.createElement('div');
            confettiPiece.classList.add('confetti-piece');
            confettiPiece.style.left = `${Math.random() * 100}%`;
            confettiPiece.style.backgroundColor = `hsl(${Math.random() * 360}, 100%, 70%)`;
            confettiPiece.style.animationDuration = `${Math.random() * 3 + 2}s`;
            confettiContainer.appendChild(confettiPiece);
        }
    }
});
function render_template(guessed_words, words, bad_guesses_count, hint_used, next_word_index, game_finished, hints_used_count, all_words_guessed, streamer_guessed) {
    // Your existing code...

    // Add a class to revealed words
    var wordBoxes = document.querySelectorAll('.word-box');
    wordBoxes.forEach(function(box, index) {
        if (guessed_words[index] !== '[ ]') {
            box.classList.add('filled');
        } else {
            box.classList.add('unknown');
        }
    });

    // Apply animation to newly guessed words
    var allWordBoxes = document.querySelectorAll('.word-box');
    allWordBoxes.forEach(function(box, index) {
        if (box.classList.contains('filled') && !box.classList.contains('revealing')) {
            box.classList.add('revealing');
        }
    });

    // Your existing code...
}
