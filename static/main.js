const hostname = "http://127.0.0.1:5000"


function createHTMLAlertMessage(message, messageType="danger") {
    let htmlMessage = document.createElement("div");
    htmlMessage.classList.add("alert", `alert-${messageType}`, "alert-dismissible", "fade", "show");
    htmlMessage.setAttribute("role", "alert");
    htmlMessage.innerHTML = message;

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
    $.ajax({
        url:`${hostname}/api/transaction/sign`,
        type:"POST",
        data:JSON.stringify(request),
        contentType:"application/json; charset=utf-8",
        dataType:"json",
        success: function (data) {
            $("#signature-mktrans").val(data["signature"]);
        },
        error: function(data) {
            let errorMessage = `An error has occurred attempting to sign this transaction<br>
                            The server returned status ${data["statusText"]}(${data["status"]}),<br>
                            with message: "${data["responseText"]}"
                            `
            $("#messages").append(createHTMLAlertMessage(errorMessage));
        }
    })
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
    $(document).on("click", ".alert button", function () {
        $(this).parent(".alert").alert("close");
    })

    $("#gen-wallet-btn").on("click", generateCryptoKeys);

    $("#sign-trans-btn").on("click", signTransaction);

    $("#broadcast-trans-btn").on("click", broadcastTransaction);

});

