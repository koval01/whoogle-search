const convert = (n1, n2, conversionFactor) => {
    const id1 = "cb" + n1;
    const id2 = "cb" + n2;
    const inputBoxValue = document.getElementById(id1).value;
    document.getElementById(id2).value = (inputBoxValue * conversionFactor).toFixed(2);
};

const currency_data = (callback, start_date, end_date, symbols, base) => {
    const url = `/currency_history?symbols=${symbols}&base=${base}&start_date=${start_date}&end_date=${end_date}`;
    ajax(url, (response) => {
        const { success, timeseries, base: responseBase, start_date: responseStartDate, end_date: responseEndDate, rates } = response;
        callback(success && timeseries && responseBase === base && responseStartDate === start_date && responseEndDate === end_date ? rates : null);
    });
};

const process_currency_data = (start_date, end_date, symbol = "UAH", base = "USD") => {
    currency_data((rates) => {
        if (!rates) return;
        const labels = Object.keys(rates);
        const vars = labels.map(label => rates[label][symbol]);
        // ...
    }, start_date, end_date, symbol, base);
};
