const hostname = "http://127.0.0.1:5000"


function generateCryptoKeys() {
    console.log($(this).text());
    $.getJSON(`${hostname}/api/wallet`, (json) => {
        $("#private-key-form-walgen").val(json["private_key"]);
        $("#public-key-form-walgen").val(json["public_key"]);
    });
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

    $("#gen-wallet-btn").on("click", generateCryptoKeys)

});

