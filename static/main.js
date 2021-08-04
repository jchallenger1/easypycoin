const hostname = "http://127.0.0.1:5000"

class MiningStats {
    constructor() {
        this.minedBlocks = 0;
        this.miningAttempts = 0;
        this.doMine = true;
    }
}

let textEncoder = new TextEncoder() // Common text encoder for encoding strings
let numZerosMining = 0; // The number of zeros the server requires for the start of a hash's block
let miningStats = new MiningStats() // Simple global class to store indicators - for this mining indicators


/*
 * General Functions
 */

// Function creates an HTML string of an alert message. The messageType dictates the coloring of said message based on bootstrap
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

// Gets all the fields from the transaction screen and puts them into a JSON string
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


// Function trims a string and adds ... between if its over a certain length, returns original string if not over length
function trimTableStr(trimStr, trimLength = 60) {
    if (trimStr.length > trimLength)
        return trimStr.substring(0, trimLength / 2) + "..." + trimStr.substring(trimStr.length - trimLength, trimStr.length);
    return trimStr;
}

// Function takes a json object and extracts all keys from keyObjects to form an HTML <tr> row
function createHTMLTableStr(jsonObject, keyObjects, lengthOfTrim = 60) {

    if (!_.every(keyObjects, (field) => {
        return field in jsonObject;
    })) {
        console.log("Error creating a table row. Missing keyObject!");
        return;
    }

    // For each JSON object we receive, add a row, keyObjects determines what properties to take from the JSON
    // object to form a row (Each th of the original table should be included in keyObjects)
    let text = `<tr>`;
    for (const key of keyObjects)
        // Add in the key data-value and data-key for easy extraction for copy button
        text += `<td data-value="${jsonObject[key]}" data-key="${key}">${trimTableStr(jsonObject[key], lengthOfTrim)}</td>`;
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

// Function calls the server repetitively to mine all blocks on the server whilst updating what was mined in the
// mining table. miningStats must be set to miningStats = new MiningStats() for the first initial call to this function
function mine() {
    $.get(`${hostname}/api/mine`, (data) => {
        let json_data = JSON.parse(data)
        // no blocks to use, either way we stop.
        if (_.isEmpty(json_data["blocks"])) {
            let status = $("#mine-status");

            // No blocks to use, first time the user even clicked this button
            if (miningStats.miningAttempts === 0) {
                $("#messages").append(createHTMLAlertMessage("There are no available blocks to mine"));
                status.html("Not mining");
            }
            else { // No blocks to use while we are mining, switch the text after a few seconds
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
        let numBlocks = json_data["blocks"].length;
        mineBlock(json_data["blocks"][_.random(0, numBlocks - 1)], miner_key).then(() => {
            // done mining a block, refresh the transaction table and mine for another block
            refreshTransactions();
            if (miningStats.doMine)
                setTimeout(mine, 250); // give server a bit of breathing room
            else
                $("#mine-status").html("Stopped Mining due to a mining failure");
        });

    });
}


// Mines a block by finding the proof of work and sending the result to the server
// base64block is a base64 string encoded in utf-8
// blockUUID is a string representing the block of the uuid
// miner_public_key is a string of the miner's key that the user entered in the html page
async function mineBlock(jsonBlock, miner_public_key) {
    // The Final mining block is [miner's key] + [server's block] + [nonce]
    let block = _base64ToArrayBuffer(jsonBlock["block"]);
    let blockUUID = jsonBlock["uuid"];

    const miningBlock = appendArrayBuffers(textEncoder.encode(miner_public_key), block);

    // Need to now find the correct nonce to get the correct hash with n amount of initial zeros
    let proof_of_work = 0;
    let proofZerosString = '0'.repeat(numZerosMining);
    for (let i = 0; i !== Number.MAX_VALUE / 100; ++i) {
        let hashBlock = appendArrayBuffers(miningBlock, textEncoder.encode(i.toString()));
        if (sha256(hashBlock).startsWith(proofZerosString)) {
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
        error: function (jqxhr) {
            ++miningStats.miningAttempts;
            // Stop mining on fatal errors
            if (jqxhr["status"] !== 401)
                miningStats.doMine = false;

            $("#mine-status").html(`Successfully Mined ${miningStats.minedBlocks}/${miningStats.miningAttempts} block attempts`);

            addToMiningTable("table-warning", jqxhr["responseText"]);
        }

    }).fail(() => {miningStats.doMine = false;});

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
// Function takes two arraybuffers and combines them together f(bf1, bf2) -> bf = bf1|bf2
function appendArrayBuffers(buffer1, buffer2) {
  let tmp = new Uint8Array(buffer1.byteLength + buffer2.byteLength);
  tmp.set(new Uint8Array(buffer1), 0);
  tmp.set(new Uint8Array(buffer2), buffer1.byteLength);
  return tmp.buffer;
}


/*
 * Button Logic Functions
 */

// Occurs when the generate wallet button is pressed
// simply asks the coinbase to generate a private/public RSA key pair
function generateCryptoKeys() {
    $.getJSON(`${hostname}/api/wallet`, (json) => {
        $("#private-key-form-walgen").val(json["private_key"]);
        $("#public-key-form-walgen").val(json["public_key"]);
    });
}

// Occurs when the button to sign a transaction is pressed
// Function gets all the data from the transaction screen and sends it to the server,
// and puts the signature into the signature text field
function signTransaction() {
    $.ajax({
        url: `${hostname}/api/transaction/sign`,
        type: "POST",
        data: getTransactionDataFieldsToJson(),
        contentType: "application/json; charset=utf-8",
        dataType: "json",
        success: function (data) {
            // put the signature onto the field
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

// Occurs when the button to broadcast a transaction is pressed
// Function gets all the data from the transaction screen and sends to server, and notifying the user if it was successful
function broadcastTransaction() {
    $.ajax({
        url: `${hostname}/api/transaction`,
        type: "POST",
        data: getTransactionDataFieldsToJson(),
        contentType: "application/json; charset=utf-8",
        dataType: "json",
        success: function () {
            // Empty the signature and uuid fields to prevent accidental multiple broadcasts
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


// Occurs when the user presses the refresh transaction button, also called directly by other functions to reset the table
// Function simply gets all non-mined transactions into the transaction table
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

// Occurs when the user presses copy on the transaction table for a specific row element
// For this, we create a json string and copy it to the user's clipboard
function copyTransactionOnTable() {
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
}

// Occurs when the user presses on the refresh block chain button
// Simply call the server for the blockchain and put it in the table.
function refreshBlockChain() {
    // Get value of the filters
    let blockUUID = $("#filter-uuid").val();
    let minerKey = $("#filter-key").val();
    let blockIndex = $("#filter-index").val();

    // Create a query string from said filters
    const params = new URLSearchParams();
    if (blockUUID) params.set("block_uuid", blockUUID);
    if (minerKey) params.set("miner_key", minerKey);
    if (blockIndex) params.set("block_index", blockIndex);
    const query = params.toString().length === 0 ? "" : "?"+ params.toString();

    // Get the blockchain with any applied filters
    $.getJSON(`${hostname}/api/chain${query}`, (data) => {
        let table = $("#blockchain-table")
        table.empty()

        for (const block of data["blocks"]) {

            block["number_of_transactions"] = block["transactions"].length;
            table.append(createHTMLTableStr(block,
                ["index", "uuid", "hash", "previous_hash", "number_of_transactions", "proof_of_work", "miner_key"],
                15));
        }
    }).fail((jqxhr) => {
        $("#messages").append(createHTMLAlertMessage(jqxhr["responseText"]));
    });
}


// Occurs when the user presses on the check balance button on the wallet generator tab
function checkBalance() {
    let public_key = $("#public-key-form-walgen").val();
    $.getJSON(`${hostname}/api/wallet/balance?public_key=${public_key}`, data => {
        // change to wallet balance
        $("#wallet-balance").val(data);
    }).fail(jqxhr => {
        $("#messages").append(createHTMLAlertMessage(jqxhr["responseText"]));
    });
}

// Occurs when the user presses on the give coins button on the wallet generator tab
function giveCoins() {
    // Get the key and the amount of coins to give, and send the data
    let public_key = $("#public-key-form-walgen").val();
    let amount = $("#wallet-give-coins-amount").val();

    $.ajax({
        url: `${hostname}/api/buy`,
        type: "POST",
        data: JSON.stringify({
            "public_key": public_key,
            "amount": amount,
        }),
        contentType: "application/json; charset=utf-8",
        dataType: "text",
        success: function (data) {
            // notify they received the coins
            $("#messages").append(createHTMLAlertMessage(data, "success"));
        }
    }).fail(jqxhr => {
        $("#messages").append(createHTMLAlertMessage(jqxhr["responseText"]));
    });
}

//
// Launcher
//
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
    $(document).on("click", ".tr-copy-btn", copyTransactionOnTable);

    $("#gen-wallet-btn").on("click", generateCryptoKeys);

    $("#sign-trans-btn").on("click", signTransaction);

    $("#broadcast-trans-btn").on("click", broadcastTransaction);

    $("#refresh-trans-button").on("click", refreshTransactions);

    $("#refresh-uuidv4-btn").on("click", () => {
        $("#uuidv4-mktrans-form").val(uuidv4()); // generate a new uuidv4
    });

    $("#mine-btn").on("click", () => {
        // When the mine button is pressed
        $("#mine-status").html(`Mined 0 blocks`);
        miningStats = new MiningStats();
        mine();
    });

    $("#clear-mining-table-btn").on("click", () => {
        // clear button on mining table, remove all rows
        $("#mining-table tr").remove();
    });

    $("#refresh-chain-btn").on("click", refreshBlockChain);

    $("#wallet-balance-btn").on("click", checkBalance);

    $("#wallet-give-coins-btn").on("click", giveCoins);

});

