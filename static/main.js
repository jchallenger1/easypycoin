const hostname = "http://127.0.0.1:5000"


function createHTMLAlertMessage(message) {
    let htmlMessage = document.createElement("div");
    htmlMessage.classList.add("alert", "alert-warning", "alert-dismissible", "fade", "show");
    htmlMessage.setAttribute("role", "alert");
    htmlMessage.textContent = message;

    let htmlButton = document.createElement("button");
    htmlButton.classList.add("close");
    htmlButton.setAttribute("type", "button");
    htmlButton.setAttribute("data-dismiss", "alert");
    htmlButton.setAttribute("aria-label",  "Close");

    let htmlButtonImg = document.createElement("span");
    htmlButtonImg.setAttribute("aria-hidden", "true");
    htmlButtonImg.textContent = "×";

    htmlButton.appendChild(htmlButtonImg);
    htmlMessage.appendChild(htmlButton);

    return htmlMessage;
}

function generateCryptoKeys() {
    $.getJSON(`${hostname}/api/wallet`, (json) => {
        $("#private-key-form-walgen").val(json["private_key"]);
        $("#public-key-form-walgen").val(json["public_key"]);
    });
}

function signTransaction() {
    let sender_private_key = $("#private-key-form-mktrans").val();
    let sender_public_key = $("#public-key-mktrans").val();
    let recipient_public_key = $("#recipient-address-mktrans").val();
    let amount = $("#amount-mktrans").val();
    let request = {
        sender_private_key,
        sender_public_key,
        recipient_public_key,
        amount
    }

    $.post(`${hostname}/api/transaction/sign`, request, (data) => {
        console.log(data);
    }).fail((data) => {
        $("#messages-trans").append(createHTMLAlertMessage("bad req"));
        console.log(data);
    });

}

function broadcastTransaction() {

}

$(document).ready(function() {
    // Allows navigation of the tabs
    $(".nav li a").on("click", () => {
        $(".nav li a").removeClass("active");
        $(this).addClass("active");
    });

    // Allows the fading out of warnings when the close button is clicked
    $(".alert button").on("click", function() {
        $(this).parent(".alert").alert("close");
    })

    $("#gen-wallet-btn").on("click", generateCryptoKeys);

    $("#sign-trans-btn").on("click", signTransaction);

    $("#broadcast-trans-btn").on("click", broadcastTransaction);

});

