// Check if the user has previously dismissed the modal
document.addEventListener("DOMContentLoaded", function() {
    const modal = document.getElementById("modal");
    const closeModal = document.querySelector(".close");
    const doNotShowAgain = document.getElementById("doNotShowAgain");
    const okButton = document.getElementById("okButton");

    // Check if the modal should be displayed
    if (!getCookie("modalDismissed")) {
        modal.style.display = "flex";
    }

    // Close the modal when the user clicks the "X" or "OK" button
    closeModal.onclick = function() {
        modal.style.display = "none";
    };
    okButton.onclick = function() {
        if (doNotShowAgain.checked) {
            setCookie("modalDismissed", "true", 365);
        }
        modal.style.display = "none";
    };

    // Function to set a cookie
    function setCookie(name, value, days) {
        const date = new Date();
        date.setTime(date.getTime() + (days * 24 * 60 * 60 * 1000));
        const expires = "expires=" + date.toUTCString();
        document.cookie = name + "=" + value + ";" + expires + ";path=/";
    }

    // Function to get a cookie
    function getCookie(name) {
        const decodedCookie = decodeURIComponent(document.cookie);
        const ca = decodedCookie.split(';');
        for (let i = 0; i < ca.length; i++) {
            let c = ca[i];
            while (c.charAt(0) === ' ') {
                c = c.substring(1);
            }
            if (c.indexOf(name + "=") === 0) {
                return c.substring(name.length + 1, c.length);
            }
        }
        return "";
    }
});
