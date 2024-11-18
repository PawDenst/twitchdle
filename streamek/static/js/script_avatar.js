document.addEventListener("DOMContentLoaded", async function() {
    let guessedStreamers = [];
    startCountdown();

    try {
        const response = await fetch('/fetch_streamer_avatar');
        if (!response.ok) {
            throw new Error('Network response was not ok');
        }
        const data = await response.json();

        const streamerList = document.getElementById('streamer-list');
        guessedStreamers = Array.from(document.querySelectorAll('.guessed-streamer-name'))
                                .map(el => el.textContent.trim().toLowerCase());

        Object.keys(data.streamers).forEach(streamer => {
            if (!guessedStreamers.includes(streamer.toLowerCase())) {
                const streamerInfo = data.streamers[streamer];
                const streamerDiv = document.createElement('div');
                streamerDiv.classList.add('streamer-item');

                const streamerImage = document.createElement('img');
                streamerImage.src = streamerInfo.Image;
                streamerImage.alt = streamer;
                streamerImage.classList.add('streamer-image-small');
                streamerDiv.appendChild(streamerImage);

                const streamerName = document.createElement('span');
                streamerName.textContent = streamer;
                streamerName.classList.add('streamer-name');
                streamerDiv.appendChild(streamerName);

                streamerDiv.addEventListener('click', function() {
                    document.getElementById('streamer').value = streamer;
                });

                streamerList.appendChild(streamerDiv);
            }
        });
    } catch (error) {
        console.error('Error fetching streamer data:', error);
    }

    const rows = document.querySelectorAll('.status-row');
    rows.forEach(function(row, rowIndex) {
        const cells = row.querySelectorAll('td');

        if (row.classList.contains('newest')) {
            cells.forEach(function(cell, cellIndex) {
                setTimeout(function() {
                    cell.classList.add('reveal');
                }, (cellIndex + 1) * 415);
            });

            setTimeout(function() {
                row.classList.remove('newest');
            }, (cells.length * 450) + 1000);
        } else {
            cells.forEach(function(cell) {
                cell.classList.add('reveal');
            });
        }
    });

    const streamerInput = document.getElementById('streamer');
    if (streamerInput) {
        streamerInput.addEventListener('input', function() {
            toggleStreamerList();
        });
    }

    function toggleStreamerList() {
        const streamerList = document.getElementById('streamer-list');
        if (!streamerInput) return;

        const filterValue = streamerInput.value.trim().toLowerCase();
        const streamerDivs = streamerList.querySelectorAll('.streamer-item');

        let hasVisibleItems = false;
        streamerDivs.forEach(function(streamerDiv) {
            const streamerName = streamerDiv.querySelector('.streamer-name').textContent.toLowerCase();
            if (streamerName.startsWith(filterValue)) {
                streamerDiv.style.display = 'block';
                hasVisibleItems = true;
            } else {
                streamerDiv.style.display = 'none';
            }
        });

        streamerList.style.display = hasVisibleItems ? 'block' : 'none';
    }

    document.addEventListener('click', function(event) {
        const streamerList = document.getElementById('streamer-list');
        if (event.target !== streamerInput && event.target.closest('#streamer-list') === null) {
            streamerList.style.display = 'none';
        }
    });

    document.querySelectorAll('form').forEach(form => {
        form.addEventListener('submit', function(event) {
            const guessButton = form.querySelector('button[name="guess"]');
            const streamerInput = document.getElementById('streamer');

            if (guessButton && event.submitter === guessButton) {
                const streamerName = streamerInput.value.trim();
                if (streamerName) {
                    // Additional logic to handle submission could go here.
                    console.log(`Streamer guessed: ${streamerName}`);
                }
            }
        });
    });

    if (document.querySelector('.congratulations')) {
        let confettiContainer = document.querySelector('.confetti');
        if (confettiContainer) {
            for (let i = 0; i < 100; i++) {
                let confettiPiece = document.createElement('div');
                confettiPiece.classList.add('confetti-piece');
                confettiPiece.style.left = `${Math.random() * 100}%`;
                confettiPiece.style.backgroundColor = `hsl(${Math.random() * 360}, 100%, 70%)`;
                confettiPiece.style.animationDuration = `${Math.random() * 3 + 2}s`;
                confettiContainer.appendChild(confettiPiece);
            }
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


});
