const updateResultStruc = () => {
    let selector = document.querySelectorAll(".ZINbbc");

    for (let el of selector) {
        el.parentNode.classList.add("parent-result-class");
    }
}

window.onload = function () {
    updateResultStruc();
}