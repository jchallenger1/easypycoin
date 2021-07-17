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

function getTransactionDataFieldsToJson() {
    let sender_private_key = $("#private-key-form-mktrans").val();
    let sender_public_key = $("#public-key-mktrans").val();
    let recipient_public_key = $("#recipient-address-mktrans").val();
    let amount = $("#amount-mktrans").val();
    let signature = $("#signature-mktrans").val();
    let uuid = $("#uuidv4-mktrans-form").val()
    let request = {
        sender_private_key,
        sender_public_key,
        recipient_public_key,
        amount,
        signature,
        uuid
    };
    return JSON.stringify(request);
}

function signTransaction() {
    $.ajax({
        url:`${hostname}/api/transaction/sign`,
        type:"POST",
        data:getTransactionDataFieldsToJson(),
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
    $.ajax({
        url:`${hostname}/api/transaction`,
        type:"POST",
        data:getTransactionDataFieldsToJson(),
        contentType:"application/json; charset=utf-8",
        dataType:"json",
        success: function () {
            $("#messages").append(createHTMLAlertMessage("Your transaction was successfully broadcast to nodes",
                "success"));
            $("#signature-mktrans").val("");
            $("#uuidv4-mktrans-form").val("");
        },
        error: function(data) {
            let errorMessage = `An error has occurred attempting to broadcast this transaction<br>
                            The server returned status ${data["statusText"]}(${data["status"]}),<br>
                            with message: "${data["responseText"]}"
                            `
            $("#messages").append(createHTMLAlertMessage(errorMessage));
        }
    });
}

function createHTMLTableStr(transaction, keyObjects) {
    let trim = (str ) => {
        if (str.length > 80)
            return str.substring(0, 40) + "..." + str.substring(str.length - 40, str.length);
        return str;
    }
    let text = `<tr>`;
    for (const key of keyObjects)
        text += `<td data-value="${transaction[key]}" data-key="${key}">${trim(transaction[key])}</td>`;
    text += `<td><button class="btn btn-primary tr-copy-btn">
                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="bi bi-clipboard" viewBox="0 0 16 16">
                  <path d="M4 1.5H3a2 2 0 0 0-2 2V14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V3.5a2 2 0 0 0-2-2h-1v1h1a1 1 0 0 1 1 1V14a1 1 0 0 1-1 1H3a1 1 0 0 1-1-1V3.5a1 1 0 0 1 1-1h1v-1z"/>
                  <path d="M9.5 1a.5.5 0 0 1 .5.5v1a.5.5 0 0 1-.5.5h-3a.5.5 0 0 1-.5-.5v-1a.5.5 0 0 1 .5-.5h3zm-3-1A1.5 1.5 0 0 0 5 1.5v1A1.5 1.5 0 0 0 6.5 4h3A1.5 1.5 0 0 0 11 2.5v-1A1.5 1.5 0 0 0 9.5 0h-3z"/>
                </svg>
                Copy
            </button></td>`;
    return text + `</tr>`;
}

function refreshTransactions() {
    $.getJSON(`${hostname}/api/transactions`, (json) => {
        for (const transaction of json){
            $("#transaction-table").append(createHTMLTableStr(transaction,
                ["sender_public_key", "recipient_public_key", "amount"]))
        }
    });
}


function textToClipboard (text) {
    let dummy = document.createElement("textarea");
    document.body.appendChild(dummy);
    dummy.value = text;
    dummy.select();
    document.execCommand("copy");
    document.body.removeChild(dummy);
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
    });

    $(document).on("click", ".tr-copy-btn", function() {
        let tr = $(this).parent().parent();
        let dict = {}
        tr.children().each(function(index, element) {
            element.getAttribute("data-key")
            if (element.hasAttribute("data-key") && element.hasAttribute("data-value"))
                dict[element.getAttribute("data-key")] = element.getAttribute("data-value");
        })
        textToClipboard(JSON.stringify(dict));

        let This = this;
        let previous = $(this).html();
        $(this).text("Copied!")
        setTimeout(function(){
            $(This).html(previous);
        }, 1000)
    });

    $("#gen-wallet-btn").on("click", generateCryptoKeys);

    $("#sign-trans-btn").on("click", signTransaction);

    $("#broadcast-trans-btn").on("click", broadcastTransaction);

    $("#refresh-trans-button").on("click", refreshTransactions);

    $("#refresh-uuidv4-btn").on("click", () => { $("#uuidv4-mktrans-form").val(uuidv4()); });
});

