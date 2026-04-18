# Data Processing/Analysis
def basic_analysis(data):
    profit = data.revenue - data.cost
    margin = profit / data.revenue if data.revenue else 0

    return {
        "profit": profit,
        "margin": margin
    }