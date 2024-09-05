async function fetchCorrectGuessesCount() {
    try {
        const response = await fetch('/correct_guesses_count');
        const data = await response.json();
        console.log('Current correct guesses count:', data.correct_guesses_count);
        document.getElementById('correctGuessesCount').innerText = data.correct_guesses_count;
    } catch (error) {
        console.error('Error fetching correct guesses count:', error);
    }
}

function startCountdown() {
    let countdownEndTime;

    function updateCountdown() {
        const now = new Date();
        let timeLeft = countdownEndTime - now;

        if (timeLeft <= 0) {
            // Time has expired, fetch new time and reset countdown
            fetch('/time_until_reset')
                .then(response => response.json())
                .then(data => {
                    const now = new Date();
                    countdownEndTime = new Date(now.getTime() + (data.hours * 3600 + data.minutes * 60 + data.seconds) * 1000);
                    updateCountdown(); // Update immediately once
                });
            return;
        }

        let hours = Math.floor(timeLeft / (1000 * 60 * 60));
        let minutes = Math.floor((timeLeft % (1000 * 60 * 60)) / (1000 * 60));
        let seconds = Math.floor((timeLeft % (1000 * 60)) / 1000);

        const countdownElement = document.getElementById('countdown');
        countdownElement.innerText = `${hours}h ${minutes}m ${seconds}s`;
    }

    // Fetch the initial time until reset
    fetch('/time_until_reset')
        .then(response => response.json())
        .then(data => {
            const now = new Date();
            countdownEndTime = new Date(now.getTime() + (data.hours * 3600 + data.minutes * 60 + data.seconds) * 1000);
            updateCountdown(); // Update immediately once
            setInterval(updateCountdown, 1000);
        });
}

// Start the countdown when the page loads
document.addEventListener('DOMContentLoaded', (event) => {
    startCountdown();
});

function addGuessedStreamerToList(streamerName, imageURL, isCorrectGuess = false) {
    const guessedStreamersList = document.getElementById('guessedStreamersList');
    const listItem = document.createElement('li');
    listItem.classList.add('guessed-streamer-item'); // Add the 'guessed-streamer-item' class

    if (isCorrectGuess) {
        listItem.classList.add('correct-guess'); // Add the new animation class for the correct guess
    }

    const streamerImage = document.createElement('img');
    streamerImage.src = imageURL || 'default-image-url.png'; // Fallback image
    streamerImage.alt = streamerName;
    streamerImage.classList.add('guessed-streamer-image');
    listItem.appendChild(streamerImage);

    const streamerSpan = document.createElement('span');
    streamerSpan.textContent = streamerName || 'Unknown Streamer';
    streamerSpan.classList.add('guessed-streamer-name');
    listItem.appendChild(streamerSpan);

    guessedStreamersList.appendChild(listItem); // Add the new item to the list

    // Apply the 'shake' animation to the oldest guessed streamer item (first item in the list) if it's not the correct guess
    const oldestItem = guessedStreamersList.firstChild;
    if (oldestItem && !isCorrectGuess) {
        oldestItem.classList.add('shake');
        // Remove the 'shake' class after the animation completes
        setTimeout(() => {
            oldestItem.classList.remove('shake');
        }, 800); // Match the duration of the animation
    }
}

function checkGameStartFlag() {
    fetch('/check_game_start_flag')
        .then(response => response.json())
        .then(data => {
            if (data.restart_game) {
                console.log('Restarting the game... Please wait.');
                listenForStartGameSignal();
                console.log('Game restarted successfully!');
            } else {
                console.log('Game not started. Received:', data);
            }
        })
        .catch(error => {
            console.error('Error receiving start game signal:', error);
        });
}
checkGameStartFlag();

function listenForStartGameSignal() {
    console.log('Listening for start game signal...');
    fetch('/trigger_start_game')
        .then(response => response.json())
        .then(data => {
            if (data.start_game) {
                console.log('Starting the game...');
                startGame();
                console.log('Game started successfully!');
            } else {
                console.log('Game not started. Received:', data);
            }
        })
        .catch(error => {
            console.error('Error receiving start game signal:', error);
        });
}

let emojisData;
let currentStreamerIndex;
let currentEmojiIndex;
let attemptsCount = 0;

async function fetchEmojisData() {
    try {
        const response = await fetch('/emojis_data');
        const data = await response.json();
        if (data.error) {
            console.error(data.error);
            throw new Error('Failed to fetch emojis data');
        }
        emojisData = data.emotes;
        currentStreamerIndex = data.streamer_index;
        const gameState = JSON.parse(localStorage.getItem('gameState'));
        if (gameState) {
            currentEmojiIndex = gameState.emojiIndex;
            attemptsCount = gameState.attemptsCount;

            if (gameState.congratulationsVisible) {
                document.getElementById('congratulations').style.display = 'block';
                document.getElementById('attemptCount').innerText = attemptsCount;
                document.getElementById('guessInput').style.display = 'none';
                document.getElementById('guessButton').style.display = 'none';
                document.getElementById('restartButton').style.display = 'block';
                showAllEmojis();

                const streamerResponse = await fetch(`/fetch_streamer_details/${currentStreamerIndex}`);
                const streamerData = await streamerResponse.json();
                const guessedStreamerImageElement = document.querySelector('.celebration-img');
                guessedStreamerImageElement.src = streamerData.image_url;

                triggerCSSConfetti();
            } else {
                renderEmojis();
            }
        } else {
            startGame();
        }
    } catch (error) {
        console.error('Error fetching emojis data:', error);
    }
}


function startGame() {
    console.log('Starting the game...');
    localStorage.removeItem('gameState');
    localStorage.removeItem('guessedStreamers');
    localStorage.removeItem('selectedStreamers');
    document.getElementById('congratulations').style.display = 'none';
    document.getElementById('guessInput').style.display = 'block';
    document.getElementById('guessButton').style.display = 'block';
    document.getElementById('restartButton').style.display = 'none';
    document.getElementById('guessInput').value = '';
    currentEmojiIndex = 0;
    attemptsCount = 0;
    saveGameState();
    renderEmojis();
    displayGuessedStreamers();
}

function renderEmojis() {
    if (!emojisData || !Array.isArray(emojisData)) {
        console.error('Emojis data is not defined or not an array.');
        return;
    }

    const emojisDiv = document.getElementById('emojis');
    emojisDiv.innerHTML = '';

    for (let i = 0; i < emojisData.length; i++) {
        const emojiSpan = document.createElement('span');

        if (i < currentEmojiIndex) {
            if (emojisData[i].startsWith('https://')) {
                const emoteImg = document.createElement('img');
                emoteImg.src = emojisData[i];
                emojiSpan.classList.add('emoji', 'show', 'large-emoji');
                emojiSpan.appendChild(emoteImg);
            } else {
                emojiSpan.innerText = emojisData[i];
                emojiSpan.classList.add('emoji', 'show', 'large-emoji');
            }
        } else if (i === currentEmojiIndex) {
            if (emojisData[i].startsWith('https://')) {
                const emoteImg = document.createElement('img');
                emoteImg.src = emojisData[i];
                emojiSpan.classList.add('emoji', 'show', 'large-emoji');
                emojiSpan.appendChild(emoteImg);
                setTimeout(() => {
                    emoteImg.classList.add('show');
                }, 0);
            } else {
                emojiSpan.innerText = emojisData[i];
                emojiSpan.classList.add('emoji', 'show', 'large-emoji');
                setTimeout(() => {
                    emojiSpan.classList.add('emoji', 'show', 'large-emoji');
                }, 0);
            }
        } else {
            const placeholderImg = document.createElement('img');
            placeholderImg.src = 'static/q2.png';
            placeholderImg.classList.add('placeholder-image');
            placeholderImg.style.marginRight = '12px';
            emojiSpan.appendChild(placeholderImg);

            placeholderImg.addEventListener('transitionend', function () {
                setTimeout(function () {
                    const nextEmojiSpan = document.createElement('span');
                    if (emojisData[i].startsWith('https://')) {
                        const emoteImg = document.createElement('img');
                        emoteImg.src = emojisData[i];
                        emojiSpan.classList.add('emoji', 'show', 'large-emoji');
                        nextEmojiSpan.appendChild(emoteImg);
                    } else {
                        nextEmojiSpan.innerText = emojisData[currentEmojiIndex];
                        emojiSpan.classList.add('emoji', 'show', 'large-emoji');
                    }
                    emojisDiv.appendChild(nextEmojiSpan);
                }, 100);
            });
        }
        emojisDiv.appendChild(emojiSpan);
    }
}
function saveGuessedStreamer(streamer, imageURL, color, isCorrectGuess) {
    let guessedStreamers = JSON.parse(localStorage.getItem('guessedStreamers')) || [];
    const existingStreamerIndex = guessedStreamers.findIndex(item => item.streamer === streamer);
    if (existingStreamerIndex !== -1) {
        // Update the color of the existing streamer
        guessedStreamers[existingStreamerIndex].color = color;
    } else {
        // Add the new streamer to the beginning of the list
        guessedStreamers.unshift({ streamer: streamer, imageURL: imageURL, color: color, isCorrectGuess: isCorrectGuess });
    }
    localStorage.setItem('guessedStreamers', JSON.stringify(guessedStreamers));
    displayGuessedStreamers(); // Refresh the display after saving
}

function displayGuessedStreamers() {
    const guessedStreamers = JSON.parse(localStorage.getItem('guessedStreamers')) || [];
    const guessedStreamersList = document.getElementById('guessedStreamersList');

    guessedStreamersList.innerHTML = ''; // Clear previous content

    guessedStreamers.forEach(streamer => {
        if (streamer.streamer && streamer.imageURL) { // Check for valid data
            addGuessedStreamerToList(streamer.streamer, streamer.imageURL, streamer.isCorrectGuess);
        }
    });
}



async function checkGuess() {
    const guessInput = document.getElementById('guessInput');
    const recaptchaResponse = document.querySelector('#recaptcha-container .g-recaptcha-response');
    const recaptchaContainer = document.getElementById('recaptcha-container');
    const captchaVerified = localStorage.getItem('captchaVerified') === 'true';

    if (!guessInput) {
        console.error('Guess input element not found.');
        return;
    }

    const guess = guessInput.value.trim().toLowerCase();
    if (guess === '') return;

    const guessButton = document.getElementById('guessButton');
    const restartButton = document.getElementById('restartButton');

    try {
        if (!captchaVerified) {
            if (!recaptchaResponse || recaptchaResponse.value === '') {
                recaptchaContainer.classList.remove('d-none');
                return;
            }

            const captchaResponse = await fetch('/verify_captcha', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    'recaptcha_response': recaptchaResponse.value
                }),
            });

            const captchaResult = await captchaResponse.json();
            if (!captchaResult.success) {
                alert('CAPTCHA verification failed. Please try again.');
                recaptchaContainer.classList.remove('d-none');
                return;
            }

            // Mark CAPTCHA as verified in localStorage
            localStorage.setItem('captchaVerified', 'true');
            recaptchaContainer.classList.add('d-none');

            // Call checkGuess() again to proceed with the guess checking
            checkGuess();
            return;
        }

        // Proceed with guess checking
        const streamerResponse = await fetch(`/fetch_streamer_details/${currentStreamerIndex}`);
        const streamerData = await streamerResponse.json();
        const correctStreamer = streamerData.streamer.toLowerCase();

        const response = await fetch('/fetch_streamer_emoji');
        if (!response.ok) throw new Error('Network response was not ok');
        const data = await response.json();

        const streamerNames = Object.keys(data.streamers).map(name => name.toLowerCase());

        // Check if the guess has already been guessed before
        const guessedStreamers = JSON.parse(localStorage.getItem('guessedStreamers')) || [];
        if (guessedStreamers.some(streamer => streamer && streamer.streamer && streamer.streamer.toLowerCase() === guess)) {
            alert('Już go sprawdzałeś!');
            guessInput.value = ''; // Clear the input field
            return;
        }

        if (streamerNames.includes(guess)) {
            if (guess === correctStreamer) {
                document.getElementById('congratulations').style.display = 'block';
                attemptsCount++;
                document.getElementById('attemptCount').innerText = attemptsCount;
                guessInput.style.display = 'none';
                guessButton.style.display = 'none';
                restartButton.style.display = 'block';
                const guessedStreamerImageElement = document.querySelector('.celebration-img');
                guessedStreamerImageElement.src = streamerData.image_url;
                document.getElementById('quoteButton');
                saveGuessedStreamer(streamerData.streamer, streamerData.image_url, 'blue', true);
                displayGuessedStreamers();
                showAllEmojis();
                triggerCSSConfetti();
                saveGameState();

                const tokenResponse = await fetch('/get_increment_token');
                const tokenData = await tokenResponse.json();
                const incrementResponse = await fetch('/increment_correct_guesses', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-Increment-Token': tokenData.token
                    }
                });
                const incrementData = await incrementResponse.json();
                console.log('Updated correct guesses count:', incrementData.correct_guesses_count);
                document.getElementById('correctGuessesCount').innerText = incrementData.correct_guesses_count;
            } else {
                attemptsCount++;
                const guessedStreamerResponse = await fetch(`/fetch_streamer_details_by_name/${guess}`);
                const guessedStreamerData = await guessedStreamerResponse.json();
                addGuessedStreamerToList(guessedStreamerData.streamer, guessedStreamerData.image_url);
                saveGuessedStreamer(guessedStreamerData.streamer, guessedStreamerData.image_url, 'grey', false);
                if (currentEmojiIndex < emojisData.length - 1) {
                    currentEmojiIndex++;
                    renderEmojis();
                    guessInput.value = '';
                }
                saveGameState();
            }
            removeStreamerFromList(guess);
        } else {
            alert('Wybierz dostępnego streamera!');
        }
    } catch (error) {
        console.error('Error fetching streamer details:', error);
    }
}



function removeStreamerFromList(streamerName) {
    let guessedStreamers = JSON.parse(localStorage.getItem('guessedStreamers')) || [];
    guessedStreamers.push(streamerName);
    localStorage.setItem('guessedStreamers', JSON.stringify(guessedStreamers));

    const streamerList = document.getElementById('streamer-list');
    const streamerItems = streamerList.querySelectorAll('.streamer-item');

    streamerItems.forEach(item => {
        const streamerNameElement = item.querySelector('.streamer-name');
        if (streamerNameElement && streamerNameElement.textContent.toLowerCase() === streamerName) {
            streamerList.removeChild(item);
        }
    });
}

function showAllEmojis() {
    if (!emojisData || !Array.isArray(emojisData)) {
        console.error('Emojis data is not defined or not an array.');
        return;
    }

    const emojisDiv = document.getElementById('emojis');
    emojisDiv.innerHTML = ''; // Clear any existing emojis

    for (let i = 0; i < emojisData.length; i++) {
        const emojiSpan = document.createElement('span');

        if (emojisData[i].startsWith('https://')) {
            const emoteImg = document.createElement('img');
            emoteImg.src = emojisData[i];
            emojiSpan.classList.add('emoji', 'show', 'large-emoji');
            emojiSpan.appendChild(emoteImg);
        } else {
            emojiSpan.innerText = emojisData[i];
            emojiSpan.classList.add('emoji', 'show', 'large-emoji');
        }
        emojisDiv.appendChild(emojiSpan);
    }
}

function triggerCanvasConfetti() {
    const end = Date.now() + 5 * 1000;

    // Confetti animation
    (function frame() {
        confetti({
            particleCount: 2,
            angle: 60,
            spread: 55,
            origin: { x: 0 }
        });
        confetti({
            particleCount: 2,
            angle: 120,
            spread: 55,
            origin: { x: 1 }
        });

        if (Date.now() < end) {
            requestAnimationFrame(frame);
        }
    }());
}

function triggerCSSConfetti() {
    let confettiContainer = document.querySelector('.confetti');
    confettiContainer.innerHTML = ''; // Clear any existing confetti

    for (let i = 0; i < 100; i++) {
        let confettiPiece = document.createElement('div');
        confettiPiece.classList.add('confetti-piece');
        confettiPiece.style.left = `${Math.random() * 100}%`;
        confettiPiece.style.backgroundColor = `hsl(${Math.random() * 360}, 100%, 70%)`;
        confettiPiece.style.animationDuration = `${Math.random() * 3 + 2}s`;
        confettiContainer.appendChild(confettiPiece);
    }
}

function saveGameState() {
    const gameState = {
        emojiIndex: currentEmojiIndex,
        attemptsCount: attemptsCount,
        congratulationsVisible: document.getElementById('congratulations').style.display === 'block'
    };
    localStorage.setItem('gameState', JSON.stringify(gameState));
}

window.addEventListener('load', () => {
    fetchEmojisData();
    displayGuessedStreamers();
    fetchCorrectGuessesCount();
});

window.addEventListener('DOMContentLoaded', function() {
    fetchEmojisData(); // Fetch emojis data when DOM content is loaded
});

window.addEventListener('beforeunload', function() {
    saveGameState();
});

window.addEventListener('DOMContentLoaded', function() {
    const gameState = JSON.parse(localStorage.getItem('gameState'));
    if (gameState) {
        currentStreamerIndex = gameState.streamerIndex;
        currentEmojiIndex = gameState.emojiIndex;
        attemptsCount = gameState.attemptsCount;
        document.getElementById('attemptCount').innerText = attemptsCount;  // Restore attempts count display
        renderEmojis();
        if (gameState.congratulationsVisible) {
            document.getElementById('congratulations').style.display = 'block';
            showAllEmojis(); // Ensure all emojis are displayed
        }
    }
    displayGuessedStreamers(); // Display guessed streamers on page load
});

// Integrate streamer list functionality
document.addEventListener("DOMContentLoaded", function() {
    fetch('/fetch_streamer_emoji')
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.json();
        })
        .then(data => {
            console.log("Streamer data fetched:", data); // Debugging: log fetched data
            const streamerList = document.getElementById('streamer-list');

            // Iterate over the streamers in the order they are received
            for (const streamer in data.streamers) {
                if (!isStreamerSelected(streamer)) {
                    const streamerInfo = data.streamers[streamer];
                    const streamerDiv = document.createElement('div');
                    streamerDiv.classList.add('streamer-item');

                    const streamerImage = document.createElement('img');
                    streamerImage.src = streamerInfo.image_url;
                    streamerImage.alt = streamer;
                    streamerImage.classList.add('streamer-image-small');
                    streamerDiv.appendChild(streamerImage);

                    const streamerName = document.createElement('span');
                    streamerName.textContent = streamer; // Display the streamer name as is
                    streamerName.classList.add('streamer-name');
                    streamerDiv.appendChild(streamerName);

                    streamerDiv.addEventListener('click', function() {
                        document.getElementById('guessInput').value = streamer.toLowerCase(); // Convert to lowercase
                        toggleStreamerList();
                    });

                    streamerList.appendChild(streamerDiv);
                }
            }

            // Display guessed streamers after fetching streamer data
            displayGuessedStreamers();
        })
        .catch(error => {
            console.error('Error fetching streamer data:', error);
        });

    document.getElementById('guessInput').addEventListener('input', function() {
        toggleStreamerList();
    });

    function toggleStreamerList() {
    const streamerList = document.getElementById('streamer-list');
    const streamerInput = document.getElementById('guessInput');
    const filterValue = streamerInput.value.trim().toLowerCase();

    fetch('/fetch_streamer_emoji')
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.json();
        })
        .then(data => {
            const streamers = data.streamers;
            streamerList.innerHTML = ''; // Clear previous content

            const guessedStreamers = JSON.parse(localStorage.getItem('guessedStreamers')) || [];
            const guessedStreamerNames = guessedStreamers
                .filter(streamerObj => streamerObj && streamerObj.streamer) // Filter out invalid entries
                .map(streamerObj => streamerObj.streamer.toLowerCase());

            for (const streamerName in streamers) {
                if (!guessedStreamerNames.includes(streamerName.toLowerCase()) && streamerName.toLowerCase().startsWith(filterValue)) {
                    const listItem = document.createElement('li');
                    listItem.classList.add('streamer-item');

                    const streamerImage = document.createElement('img');
                    streamerImage.src = streamers[streamerName].image_url;
                    streamerImage.alt = streamerName;
                    streamerImage.classList.add('streamer-image-small');
                    listItem.appendChild(streamerImage);

                    const streamerSpan = document.createElement('span');
                    streamerSpan.textContent = streamerName;
                    streamerSpan.classList.add('streamer-name');
                    listItem.appendChild(streamerSpan);

                    listItem.addEventListener('click', function() {
                        document.getElementById('guessInput').value = streamerName.toLowerCase();
                        streamerList.style.display = 'none';
                    });

                    streamerList.appendChild(listItem);
                }
            }

            if (filterValue !== '') {
                streamerList.style.display = 'block';
            } else {
                streamerList.style.display = 'none';
            }
        })
        .catch(error => {
            console.error('Error fetching streamers:', error);
        });
}


document.getElementById('guessInput').addEventListener('keypress', function(event) {
    if (event.key === 'Enter') {
        checkGuess();
    }
});



function addGuessedStreamer(streamerName) {
    const guessedStreamers = JSON.parse(localStorage.getItem('guessedStreamers')) || [];
    guessedStreamers.push(streamerName);
    localStorage.setItem('guessedStreamers', JSON.stringify(guessedStreamers));
}

function updateGuessedStreamersList(streamerName) {
    const guessedStreamersList = document.getElementById('guessedStreamersList');
    const listItem = document.createElement('li');
    listItem.textContent = streamerName;
    guessedStreamersList.appendChild(listItem);
}

document.getElementById('guessInput').addEventListener('input', toggleStreamerList);

function isStreamerGuessed(streamer) {
    let guessedStreamers = JSON.parse(localStorage.getItem('guessedStreamers')) || [];
    return guessedStreamers.some(item => item.streamer.toLowerCase() === streamer);
}

    document.addEventListener('click', function(event) {
    const streamerInput = document.getElementById('guessInput');
    const streamerList = document.getElementById('streamer-list');
    if (event.target !== streamerInput && event.target.parentNode !== streamerList) {
        streamerList.style.display = 'none';
    }
});


    document.addEventListener('DOMContentLoaded', function() {
    toggleStreamerList();
});

    document.addEventListener("DOMContentLoaded", function() {
    const formElement = document.querySelector('form');
    if (formElement) {
        formElement.addEventListener('submit', function(event) {
            event.preventDefault(); // Prevent default form submission behavior
            const streamerName = document.getElementById('guessInput').value;
            if (streamerName) {
                saveSelectedStreamer(streamerName);
            }
        });
    } else {
        console.error('No form element found in the document');
    }
});

function saveSelectedStreamer(streamer) {
    let selectedStreamers = JSON.parse(localStorage.getItem('selectedStreamers')) || [];
    if (!selectedStreamers.includes(streamer)) {
        selectedStreamers.push(streamer);
        localStorage.setItem('selectedStreamers', JSON.stringify(selectedStreamers));
    }
}

function isStreamerSelected(streamer) {
    let selectedStreamers = JSON.parse(localStorage.getItem('selectedStreamers')) || [];
    return selectedStreamers.includes(streamer);
}


});



