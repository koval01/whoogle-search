const convert = (n1, n2, conversionFactor) => {
    // id's for currency input boxes
    let id1 = "cb" + n1; 
    let id2 = "cb" + n2;
    // getting the value of the input box that just got filled
    let inputBox = document.getElementById(id1).value;
    // updating the other input box after conversion
    document.getElementById(id2).value = ((inputBox * conversionFactor).toFixed(2));
}

const currency_data = (callback, start_date, end_date, symbols, base) => {
    ajax(`/currency_history?symbols=${symbols}&base=${base}&start_date=${start_date}&end_date=${end_date}`,
        function (r) {
            if (
                r.success && r.timeseries &&
                r.base === base &&
                r.start_date === start_date &&
                r.end_date === end_date) {
                callback(r.rates)
            } else {
                callback(null)
            }
        }
    )
}

const build_currency_chart = (start_date, end_date, symbol = "UAH", base = "USD") => {
    currency_data(function (r) {
        const labels = Object.keys(r);
        let vars = [];
        for (let i = 0; i < labels.length; i++) {
            vars.push(r[labels[i]][symbol])
        }

        const data = {
            labels: labels,
            datasets: [{
                label: `${base}/${symbol}`,
                backgroundColor: 'rgb(77, 77, 77)',
                borderColor: 'rgb(77, 77, 77)',
                data: vars,
            }]
        };

        const config = {
            type: 'line',
            data: data,
            options: {}
        };

        const selector = document.getElementById('currency_chart_display');
        selector.style.display = ""
        new Chart(
            selector,
            config
        );
    }, start_date, end_date, symbol, base);
}