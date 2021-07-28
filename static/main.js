const hostname = "http://127.0.0.1:5000"

class MiningStats {
    constructor() {
        this.minedBlocks = 0;
        this.miningAttempts = 0;
    }
}

let textEncoder = new TextEncoder() // Common text encoder for encoding strings
let numZerosMining = 0; // The number of zeros the server requires for the start of a hash's block
let miningStats = new MiningStats()



// Function creates an HTML string of an alert message. The messageType dictates the coloring of said message
function createHTMLAlertMessage(message, messageType = "danger") {
    let htmlMessage = document.createElement("div");
    htmlMessage.classList.add("alert", `alert-${messageType}`, "alert-dismissible", "fade", "show");
    htmlMessage.setAttribute("role", "alert");
    htmlMessage.innerHTML = message;

    let htmlButton = document.createElement("button");
    htmlButton.classList.add("close");
    htmlButton.setAttribute("type", "button");
    htmlButton.setAttribute("data-dismiss", "alert");
    htmlButton.setAttribute("aria-label", "Close");

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
    return JSON.stringify({
        "sender_private_key": $("#private-key-form-mktrans").val(),
        "sender_public_key": $("#public-key-mktrans").val(),
        "recipient_public_key": $("#recipient-address-mktrans").val(),
        "amount": $("#amount-mktrans").val(),
        "signature": $("#signature-mktrans").val(),
        "uuid": $("#uuidv4-mktrans-form").val(),
    });
}

function signTransaction() {
    $.ajax({
        url: `${hostname}/api/transaction/sign`,
        type: "POST",
        data: getTransactionDataFieldsToJson(),
        contentType: "application/json; charset=utf-8",
        dataType: "json",
        success: function (data) {
            $("#signature-mktrans").val(data["signature"]);
        },
        error: function (data) {
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
        url: `${hostname}/api/transaction`,
        type: "POST",
        data: getTransactionDataFieldsToJson(),
        contentType: "application/json; charset=utf-8",
        dataType: "json",
        success: function () {
            $("#messages").append(createHTMLAlertMessage("Your transaction was successfully broadcast to nodes",
                "success"));
            $("#signature-mktrans").val("");
            $("#uuidv4-mktrans-form").val("");
        },
        error: function (data) {
            let errorMessage = `An error has occurred attempting to broadcast this transaction<br>
                            The server returned status ${data["statusText"]}(${data["status"]}),<br>
                            with message: "${data["responseText"]}"
                            `
            $("#messages").append(createHTMLAlertMessage(errorMessage));
        }
    });
}

// Function trims a string and adds ... between if its over a certain length, returns original string if not over length
function trimTableStr(trimStr) {
    if (trimStr.length > 60)
        return trimStr.substring(0, 30) + "..." + trimStr.substring(trimStr.length - 30, trimStr.length);
    return trimStr;
}

// Function takes a transaction object and extracts all keys from keyObjects to form an HTML <tr> row
function createHTMLTableStr(transaction, keyObjects) {

    if (!_.every(keyObjects, (field) => {
        return field in transaction;
    })) {
        console.log("Error creating a table row. Missing keyObject!");
        return;
    }

    // For each transaction JSON object we receive, add a row, keyObjects determines what properties to take from the JSON
    // object to form a row (Each th of the original table should be included in keyObjects)
    let text = `<tr>`;
    for (const key of keyObjects)
        // Add in the key data-value and data-key for easy extraction for copy button
        text += `<td data-value="${transaction[key]}" data-key="${key}">${trimTableStr(transaction[key])}</td>`;
    // Create a copy button
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
        let table = $("#view-trans-table")
        table.empty()
        for (const transaction of json) {
            table.append(createHTMLTableStr(transaction,
                ["uuid", "sender_public_key", "recipient_public_key", "amount"]));
        }
    });
}

// Function copies text to the user's clipboard
function textToClipboard(text) {
    // To copy, it requires a DOM element to use the copy command
    let dummy = document.createElement("textarea");
    document.body.appendChild(dummy);
    dummy.value = text;
    dummy.select();
    document.execCommand("copy");
    document.body.removeChild(dummy);
}

$(document).ready(function () {
    // Get the number of zeros per hash
    $.get(`${hostname}/api/mine/numzeros`, function(data) {
       numZerosMining = parseInt(data);
    });

    // Allows navigation of the tabs
    $(".nav li a").on("click", () => {
        $(".nav li a").removeClass("active");
        $(this).addClass("active");
    });

    // Allows the fading out of warnings when the close button is clicked
    $(document).on("click", ".alert button", function () {
        $(this).parent(".alert").alert("close");
    });

    // On View and managing transactions, when the copy button is clicked to copy that said row
    $(document).on("click", ".tr-copy-btn", function () {
        let tr = $(this).parent().parent();
        // Create a dictionary and go through the row to populate the dictionary
        let dict = {}
        tr.children().each(function (index, element) {
            element.getAttribute("data-key")
            if (element.hasAttribute("data-key") && element.hasAttribute("data-value"))
                dict[element.getAttribute("data-key")] = element.getAttribute("data-value");
        });

        textToClipboard(JSON.stringify(dict));

        // Animate a "Copied!" message onto the button and return back to the original image
        let This = this;
        let previous = $(this).html();
        $(this).text("Copied!")
        setTimeout(function () {
            $(This).html(previous);
        }, 1000)
    });

    $("#gen-wallet-btn").on("click", generateCryptoKeys);

    $("#sign-trans-btn").on("click", signTransaction);

    $("#broadcast-trans-btn").on("click", broadcastTransaction);

    $("#refresh-trans-button").on("click", refreshTransactions);

    $("#refresh-uuidv4-btn").on("click", () => {
        $("#uuidv4-mktrans-form").val(uuidv4());
    });

    $("#mine-btn").on("click", () => {
        $("#mine-status").html(`Mined 0 blocks`);
        miningStats = new MiningStats();
        mine();
    });
    $("#clear-mining-table-btn").on("click", () => {
        $("#mining-table tr").remove();
    });

});

function mine() {

    $.get(`${hostname}/api/mine`, (data) => {
        let json_data = JSON.parse(data)
        // no blocks to use
        if (_.isEmpty(json_data["blocks"])) {
            let status = $("#mine-status");

            // No blocks to use, first time the user even clicked this button
            if (miningStats.miningAttempts === 0) {
                $("#messages").append(createHTMLAlertMessage("There are no available blocks to mine"));
                status.html("Not mining");
            }
            else { // No blocks to use while we are mining, switch after a few seconds
                setTimeout(() => {
                    if (miningStats.miningAttempts !== 0)
                        status.html("Not mining");
                }, 5000);
            }

            return;
        }

        const miner_key = $("#miner-public-key").val();

        // There is no point mining each block async because as soon as one is finished, all the others we have are invalid,
        // so instead just choose one random one and focus on it
        let numBlocks = json_data["blocks"].length
        mineBlock(json_data["blocks"][_.random(0, numBlocks - 1)], miner_key).then(() => {
            refreshTransactions()
            mine();
        });

    });
}


// Mines a block by finding the proof of work and sending the result to the server
// base64block is a base64 string encoded in utf-8
// blockuuid is a string representing the block of the uuid
// miner_public_key is a string of the miner's key that the user entered in the html page
async function mineBlock(jsonblock, miner_public_key) {
    // The Final mining block is [miner's key] + [server's block] + [nonce]
    let block = _base64ToArrayBuffer(jsonblock["block"]);
    let blockUUID = jsonblock["uuid"];

    const miningBlock = appendArrayBuffers(textEncoder.encode(miner_public_key), block);

    // Need to now find the correct nonce to get the correct hash with n amount of initial zeros
    let proof_of_work = 0;
    for (let i = 0; i !== Number.MAX_VALUE / 100; ++i) {
        let hashBlock = appendArrayBuffers(miningBlock, textEncoder.encode(i.toString()));
        if (sha256(hashBlock).startsWith('0'.repeat(numZerosMining))) {
            proof_of_work = i;
            break;
        }

    }

    // Found it, now send it to the server
    const jsonPostData = JSON.stringify({
                            "proof_of_work": proof_of_work.toString(),
                            "uuid": blockUUID,
                            "miner_public_key": miner_public_key});

    // Function adds a new row to the mining table with the result of this block
    const addToMiningTable = (rowType, message) => {
        $("#mining-table").append(
            `<tr class="${rowType}">
                <th>${blockUUID}</th>
                <th>${message}</th>
            </tr>`)
    }

    $.ajax({
        url: `${hostname}/api/mine`,
        type: "POST",
        data:jsonPostData,
        contentType: "application/json; charset=utf-8",
        dataType: "text",
        success: function (data) {
            // update mining stats
            ++miningStats.miningAttempts;
            ++miningStats.minedBlocks;

            // Set the mining status
            $("#mine-status").html(`Successfully Mined ${miningStats.minedBlocks}/${miningStats.miningAttempts} block attempts`);
            addToMiningTable("table-success", data);
        },
        error: function (data) {
            ++miningStats.miningAttempts;

            $("#mine-status").html(`Successfully Mined ${miningStats.minedBlocks}/${miningStats.miningAttempts} block attempts`);
            addToMiningTable("table-warning", data);
        }
    });

}

// https://stackoverflow.com/questions/21797299/convert-base64-string-to-arraybuffer
// Function turns a base 64 string into an arraybuffer
function _base64ToArrayBuffer(base64str) {
    let binary_string = atob(base64str);
    let len = binary_string.length;
    let bytes = new Uint8Array(len);
    for (let i = 0; i < len; i++) {
        bytes[i] = binary_string.charCodeAt(i);
    }
    return bytes.buffer;
}


// https://gist.github.com/72lions/4528834
// Function takes two arraybuffers and combines them together f(bf1, bf2) -> bf1|bf2
function appendArrayBuffers(buffer1, buffer2) {
  let tmp = new Uint8Array(buffer1.byteLength + buffer2.byteLength);
  tmp.set(new Uint8Array(buffer1), 0);
  tmp.set(new Uint8Array(buffer2), buffer1.byteLength);
  return tmp.buffer;
}