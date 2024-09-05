document.addEventListener("DOMContentLoaded", async function() {
    let guessedStreamers = [];

    try {
        const response = await fetch('/fetch_streamer_quote');
        if (!response.ok) {
            throw new Error('Network response was not ok');
        }
        const data = await response.json();

        const streamerList = document.getElementById('streamer-list');
        guessedStreamers = Array.from(document.querySelectorAll('.guessed-streamer-name')).map(el => el.textContent.trim().toLowerCase());

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
        const streamerInput = document.getElementById('streamer');
        if (!streamerInput) return;

        const filterValue = streamerInput.value.trim().toLowerCase();

        const streamerDivs = streamerList.querySelectorAll('.streamer-item');
        streamerDivs.forEach(function(streamerDiv) {
            const streamerName = streamerDiv.querySelector('.streamer-name').textContent.toLowerCase();
            if (streamerName.startsWith(filterValue)) {
                streamerDiv.style.display = 'block';
            } else {
                streamerDiv.style.display = 'none';
            }
        });

        if (filterValue !== '') {
            streamerList.style.display = 'block';
        } else {
            streamerList.style.display = 'none';
        }
    }

    document.addEventListener('click', function(event) {
        const streamerInput = document.getElementById('streamer');
        const streamerList = document.getElementById('streamer-list');
        if (event.target !== streamerInput && event.target.parentNode !== streamerList) {
            streamerList.style.display = 'none';
        }
    });

    document.querySelectorAll('form').forEach(form => {
    form.addEventListener('submit', function(event) {
        const guessButton = form.querySelector('button[name="guess"]');
        const hintButton = form.querySelector('button[name="hint"]');
        const streamerInput = document.getElementById('streamer');

        if (guessButton && event.submitter === guessButton) {
            const streamerName = streamerInput.value.trim();
            const streamerNameLower = streamerName.toLowerCase();
            }
    });
});

});

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
