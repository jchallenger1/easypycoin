const hostname = "http://127.0.0.1:5000"


function genKeys() {
    $.get(`${hostname}/api/wallet`, (data, status) => {
        console.log(data);
    });
}

$(document).ready(function() {
    $(".nav li a").on("click", () => {
        console.log("clicked!")
        $(".nav li a").removeClass("active");
        $(this).addClass("active");
    });
});

