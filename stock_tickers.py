from dash.react import Dash
from flask import Flask
import finsymbols
import colorlover as cl
from dash_core_components import Graph, Dropdown, Input, Slider
import dash_html_components as html
import datetime as dt
import itertools
import json
import os
import pandas as pd
import pandas_datareader.data as web
import plotly
import traceback


server = Flask(__name__)
dash = Dash(__name__, server=server)
dash.css.append_css({
    'external_url': (
        "https://cdnjs.cloudflare.com/ajax/libs/skeleton"
        "/2.0.4/skeleton.min.css"
    )
})

# World Bank Example
colorscale = cl.scales['9']['qual']['Paired']
df = pd.read_csv('./WDI_Data_Filtered.csv', encoding='latin1')
indicators = {
    'World view': [
        'Population density (people per sq. km of land area)',
        'GNI per capita, PPP (current international $)'
    ],
    'People': [
        'Income share held by lowest 20%',
        'Life expectancy at birth, total (years)',
        'Fertility rate, total (births per woman)',
        'Gross enrollment ratio, primary, both sexes (%)',
        'Gross enrolment ratio, secondary, both sexes (%)',
        'Prevalence of HIV, total (% of population ages 15-49)'
    ],
    'Environment': [
        'Energy use (kg of oil equivalent per capita)',
        'CO2 emissions (metric tons per capita)',
        'Electric power consumption (kWh per capita)'
    ],
    'Economy': [
        'GDP growth (annual %)',
        'Inflation, GDP deflator (annual %)',
        'Agriculture, value added (% of GDP)',
        'Industry, value added (% of GDP)',
        'Services, etc., value added (% of GDP)',
        'Exports of goods and services (% of GDP)',
        'Imports of goods and services (% of GDP)',
        'Revenue, excluding grants (% of GDP)',
        'Net lending (+) / net borrowing (-) (% of GDP)'
    ],
    'States and market': [
        'Time required to start a business (days)',
        'Domestic credit provided by financial sector (% of GDP)',
        'Tax revenue (% of GDP)',
        'Military expenditure (% of GDP)',
        'Mobile cellular subscriptions (per 100 people)',
        'Internet users (per 100 people)',
        'High-technology exports (% of manufactured exports)'
    ]
}

options = []
for k, v in indicators.iteritems():
    options.append({'label': k, 'value': k, 'disabled': True})
    for i in v:
        options.append({'label': i, 'value': i})

world_bank_layout = html.Div([
    html.H2('Market Indicators'),
    html.H4('Dash Developer Preview App'),

    html.Hr(),

    Dropdown(id='indicator-dropdown-single',
             options=options,
             value='GDP growth (annual %)'),

    html.Div([
        html.Div([
            Graph(id='choropleth'),
            Graph(id='indicator-over-time'),
        ], className="eight columns"),

        html.Div([Slider(id='year-slider')],
            style={'marginTop': 25, 'marginBottom': 25}
        ),

        html.Div(id='table',
                 style={'height': '850px', 'overflowY': 'scroll'},
                 className="four columns"),
    ], className="row"),

    html.Hr(),

    html.H3('Indicators over Time'),

    html.Div([
        html.Div([
            html.Label('Indicator'),
            Dropdown(
                id='indicator-dropdown',
                options=options,
                multi=True,
                value=[
                    'Exports of goods and services (% of GDP)',
                    'Imports of goods and services (% of GDP)'
                ]
            ),

            html.Label('Region'),
            Dropdown(
                id='region-dropdown',
                options=[{'label': i, 'value': i}
                         for i in list(df['Country Name'].unique())],
                multi=True,
                value=['Kuwait', 'United States', 'United Kingdom']
            )
        ], className="three columns"),

        html.Div([
            Graph(id='indicator-time-series'),
        ], className="nine columns")


    ], className="row"),

    html.Hr(),
])

@dash.react('indicator-time-series', ['indicator-dropdown', 'region-dropdown'])
def update_graph(indicator_dropdown, region_dropdown):
    indicators = indicator_dropdown['value']
    regions = region_dropdown['value']
    years = [str(i) for i in range(1960, 2017)]

    figure = plotly.tools.make_subplots(
        rows=len(indicators), cols=1, subplot_titles=indicators,
        shared_xaxes=True, vertical_spacing=0.03
    )
    figure['layout']['height'] = 300 * len(indicators)
    figure['layout']['margin'] = {'l': 20, 't': 40, 'r': 0, 'b': 0, 'pad': 0}
    figure['layout']['legend'] = {'x': 0, 'y': 1, 'bgcolor': 'rgba(255, 255, 255, 0.5)'}

    fdf = df[
        df['Indicator Name'].isin(indicators) &
        df['Country Name'].isin(regions)
    ]

    for indicator in indicators:
        df_indicator = fdf[(fdf['Indicator Name'] == indicator)]
        for region in regions:
            color = colorscale[regions.index(region) % len(colorscale)]
            try:
                row = df_indicator[
                        (df_indicator['Country Name'] == region)
                    ].ix[:, '1960':].irow(0).tolist()
            except:
                row = []
            trace = {
                'x': years,
                'y': row,
                'name': region,
                'legendgroup': region,
                'showlegend': True if indicators.index(indicator) == 0 else False,
                'marker': {'size': 10, 'color': color},
                'line': {'width': 3, 'color': color},
                'mode': 'lines+markers',
                'connectgaps': True
            }

            figure.append_trace(trace, indicators.index(indicator) + 1, 1)

    return {'figure': figure}
    fdf = df[df['Indicator Name'] == indicator]

@dash.react('year-slider', ['indicator-dropdown-single'])
def update_slider(indicator_dropdown):
    indicator = indicator_dropdown['value']
    fdf = df[df['Indicator Name'] == indicator]
    available_years = [
        year for year in range(1960, 2017)
        if not fdf[str(year)].isnull().values.all()
    ]

    return {
        'value': available_years[-1],
        'marks': {year: str(year) if (i%5 == 0 or len(available_years) < 10) else ''
                  for i, year in enumerate(available_years)},
        'step': None,
        'min': min(available_years),
        'max': max(available_years)
    }


@dash.react('choropleth', ['indicator-dropdown-single', 'year-slider'])
def update_choropleth(indicator_dropdown, year_slider):
    indicator = indicator_dropdown['value']
    year = str(year_slider['value'])
    fdf = df[df['Indicator Name'] == indicator]
    return {'figure': {
        'data': [{
            'type': 'choropleth',
            'locations': fdf['Country Name'],
            'z': fdf[year],
            'locationmode': 'country names',
            'colorscale': 'Viridis',
            'colorbar': {
                'x': 1,
                'len': 0.5,
                'outlinewidth': 0,
                'xpad': 0, 'ypad': 0,
                'thickness': 10
            }
        }],
        'layout': {
            'margin': {'l': 0, 'r': 0, 't': 0, 'b': 0, 'pad': 0},
            'geo': {'showframe': False},
            'width': '100%'
        }
    }}


@dash.react('table', ['indicator-dropdown-single', 'year-slider'])
def update_table(indicator_dropdown, year_slider):
    indicator = indicator_dropdown['value']
    year = str(year_slider['value'])
    fdf = df[df['Indicator Name'] == indicator]\
        .sort_values(year, ascending=False)
    countries = fdf['Country Name'].tolist()
    values = fdf[year].tolist()
    return {'content': html.Table(
        [html.Tr([html.Th('Country'), html.Th(indicator)])] +
        [html.Tr([
            html.Td(country), html.Td(str(value))
        ]) for country, value in zip(countries, values)]
    )}

@dash.react('indicator-over-time',
            events=[
                {'id': 'choropleth', 'event': 'hover'},
                {'id': 'indicator-dropdown-single', 'event': 'propChange'}
            ],
            state=[
                {'id': 'choropleth', 'prop': 'hoverData'},
                {'id': 'indicator-dropdown-single', 'prop': 'value'}
            ])
def graph_country_data(eventData, indicator):
    if 'points' in eventData:
        country_code = eventData['points'][0]['location']
    else:
        country_code = 'USA'

    fdf = df[(df['Indicator Name'] == indicator) &
             (df['Country Code'] == country_code)]
    country_name = fdf['Country Name'].irow(0)
    x = fdf.ix[:, '1960':].columns
    y = fdf.ix[:, '1960':].irow(0)

    return {
        'figure': {
            'data': [{
                'x': x,
                'y': y,
                'mode': 'markers+lines',
                'marker': {'size': 8},
                'line': {'width': 2}
            }],
            'layout': {
                'margin': {'l': 20, 'r': 0, 't': 0, 'b': 40},
                'yaxis': {'showgrid': None},
                'xaxis': {'showgrid': None},
                'annotations': [{
                    'x': 0, 'y': 1,
                    'text': '{} over time in {}'.format(indicator, country_name),
                    'xref': 'paper', 'yref': 'paper',
                    'font': {'size': 16}, 'showarrow': False
                }]
            }
        }
    }

# Stock Tickers Example
symbols = finsymbols.get_sp500_symbols()
stock_ticker_layout = html.Div([
    html.H3('S&P 500', id='h1'),
    html.Div([
        html.Div([
            Dropdown(
                id='stock-ticker-input',
                options=[{'label': s['company'], 'value': s['symbol']} for s in symbols],
                value=['YHOO'],
                multi=True
            )
        ], className="two columns"),

        html.Div([Graph(id='s&p-graph')], className="ten columns")

    ], className="row")

])


# list of tickers
df_companies = pd.read_csv('https://raw.githubusercontent.com/'
                           'plotly/dash/master/companylist.csv')
tickers = [s.lower() for s in list(df_companies['Symbol'])]

def bbands(price, window_size=10, num_of_std=5):
    rolling_mean = price.rolling(window=window_size).mean()
    rolling_std  = price.rolling(window=window_size).std()
    upper_band = rolling_mean + (rolling_std*num_of_std)
    lower_band = rolling_mean - (rolling_std*num_of_std)
    return rolling_mean, upper_band, lower_band

@dash.react('s&p-graph', ['stock-ticker-input'])
def update_graph(stock_ticker_input):
    """ This function is called whenever the input
    'stock-ticker-input' changes.
    Query yahoo finance with the ticker input and update the graph
    'graph' with the result.
    """
    tickers = stock_ticker_input['value']
    traces = []
    for i, ticker in enumerate(tickers):
        df = web.DataReader(ticker, 'yahoo',
                            dt.datetime(2016, 6, 1),
                            dt.datetime(2017, 2, 15))
        candlestick = {
            'x': df.index,
            'open': df['Open'],
            'high': df['High'],
            'low': df['Low'],
            'close': df['Close'],
            'type': 'candlestick',
            'name': ticker,
            'legendgroup': ticker,
            'increasing': {'line': {'color': colorscale[(i*2) % len(colorscale)]}},
            'decreasing': {'line': {'color': colorscale[(i*2 + 1) % len(colorscale)]}}
        }
        bb_bands = bbands(df.Close)
        bollinger_traces = [{
            'x': df.index, 'y': y,
            'type': 'scatter', 'mode': 'lines',
            'line': {'width': 1, 'color': colorscale[(i*2) % len(colorscale)]},
            'hoverinfo': 'none',
            'legendgroup': ticker,
            'showlegend': True if i == 0 else False,
            'name': '{} - bollinger bands'.format(ticker)
        } for i, y in enumerate(bb_bands)]
        traces.append(candlestick)
        traces.extend(bollinger_traces)

    return {
        'figure': {
            'data': traces,
            'layout': {
                'margin': {'b': 50, 'r': 10, 'l': 60, 't': 0}
            }
        }
    }


dash.layout = html.Div([
    world_bank_layout, stock_ticker_layout
], style={'marginLeft': 20, 'marginRight': 20})

dash._setup_server()
if __name__ == '__main__':
    dash.server.run(debug=True)
