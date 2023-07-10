import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from dash import Dash, Input, Output, State, dash_table, dcc, html
from dash.exceptions import PreventUpdate

ehDebug = False

def onoff_print(texto):
    if ehDebug:
        print(texto)

def acessar_dados_de_entrada(
        dados, 
        planilha_anterior, 
        planilha_atual, 
        planilha_eqv, 
):
    df_ppc_1 = dados[planilha_anterior]
    df_ppc_1['Disciplina'] = df_ppc_1['Disciplina'].str.strip()
    df_ppc_1 = df_ppc_1.set_index('Disciplina')

    df_ppc_2 = dados[planilha_atual]
    df_ppc_2['Disciplina'] = df_ppc_2['Disciplina'].str.strip()
    df_ppc_2 = df_ppc_2.set_index('Disciplina')

    df_eqv = dados[planilha_eqv]
    df_eqv['Disciplina_1'] = df_eqv['Disciplina_1'].str.strip()
    df_eqv['Disciplina_2'] = df_eqv['Disciplina_2'].str.strip()

    # Se tiver alguma equivalência de disciplinas que não aparecem 
    # nos ppc's 1 e 2, quero retirar da lista e avisar.
    flag_in1 = [(item in df_ppc_1.index) for item in df_eqv['Disciplina_1']]
    flag_in2 = [(item in df_ppc_2.index) for item in df_eqv['Disciplina_2']]
    flag_out1 = [(not item) for item in flag_in1]
    flag_out2 = [(not item) for item in flag_in2]

    if any(flag_out1) or any(flag_out2):
        onoff_print('Retiradas da lista - 2 disciplinas fora:\n')
        flag = [(item1 and item2) for item1, item2 in zip(flag_out1, flag_out2)]
        onoff_print(f'{df_eqv[flag]}\n\n')

        onoff_print('Retiradas da lista - disciplina fora apenas em 1:\n')
        flag = [(item1 and item2) for item1, item2 in zip(flag_out1, flag_in2)]
        onoff_print(f'{df_eqv[flag]}\n\n')

        onoff_print('Retiradas da lista - disciplina fora apenas em 2:\n')
        flag = [(item1 and item2) for item1, item2 in zip(flag_in1, flag_out2)]
        onoff_print(f'{df_eqv[flag]}\n\n')

    flag = [(item1 and item2) for item1, item2 in zip(flag_in1, flag_in2)]
    df_eqv = df_eqv[flag].copy()

    disc_com_aumento_1, disc_com_aumento_2 = \
        obter_lista_de_disciplinas_para_dispensa(df_eqv, df_ppc_1, df_ppc_2)

    return df_ppc_1, df_ppc_2, df_eqv, disc_com_aumento_1, disc_com_aumento_2

def montar_resumo_ppc(
        df_ppc, 
        disciplinas_ok, 
        CH_optativa,
        minha_ordem_periodos,
):
    onoff_print(f'montar_resumo_ppc:')

    aux = []
    for item in minha_ordem_periodos:
        dff = df_ppc[df_ppc['Período'] == item]

        flag_cursada = [(idx in disciplinas_ok) for idx, row in dff.iterrows()]

        # Apenas "Optativas" tem créditos necessários: "CH_optativa".

        if item == 'Optativas':
            ch_cursada = sum(dff.loc[flag_cursada, 'CH'])
            ch_restante = (CH_optativa - ch_cursada) if (CH_optativa - ch_cursada) > 0 else 0
            perc_restante = 100*ch_restante/CH_optativa
            perc_cursada = 100 - perc_restante
        else:
            ch_cursada = sum(dff.loc[flag_cursada, 'CH'])
            ch_total = sum(dff['CH'])
            ch_restante = ch_total - ch_cursada
            perc_restante = 100*ch_restante/ch_total
            perc_cursada = 100*ch_cursada/ch_total

        aux.append(
            {
                'Tipo': item,
                'CH_cursada': ch_cursada, 
                '%_cursada': f'{perc_cursada:.2f}', 
                'CH_restante': ch_restante, 
                '%_restante': f'{perc_restante:.2f}', 
            }
        )

        if 'Extensão' in dff.columns:
            aux[-1]['Extensão'] = f"{sum(dff.loc[flag_cursada, 'Extensão'])} de {sum(dff['Extensão'])}"

    return pd.DataFrame(aux, index=minha_ordem_periodos)

def montar_resumo_ppc_dee_ufpb_generalista(
        df_ppc, 
        disciplinas: list, 
        CH_optativa,
        minha_ordem_periodos,
):
    onoff_print(f'montar_resumo_ppc:')

    disciplinas_ok = [item for item in disciplinas]

    aux = []
    for item in minha_ordem_periodos:
        dff = df_ppc[df_ppc['Período'] == item]

        flag_cursada = [(idx in disciplinas_ok) for idx, row in dff.iterrows()]

        # Apenas "Optativas" tem créditos necessários: "CH_optativa".

        if item == 'Optativas':
            # Existe o limite de 8 créditos por ênfase...
            ch_cursada = 0
            for enfase in ['ELE', 'C&A', 'SDE']:

                onoff_print(f'disciplinas_ok = {disciplinas_ok}\n\n')

                planilha = dict_config['enfases_ppc_1'][enfase]['planilha']
                df_enfase = dados[planilha]
                df_enfase['Disciplina'] = df_enfase['Disciplina'].str.strip()
                df_enfase = df_enfase.set_index('Disciplina')

                # Observe que o 8° período foi incluído para pegar as optativas 
                # obrigatórias como optativas para o generalista.
                dff_enfase = df_enfase[df_enfase['Período'].isin(['8° período', 'Optativas'])]
                onoff_print(f'dff_enfase = {dff_enfase}\n\n')

                flag_enfase = [(idx in disciplinas_ok) for idx, row in dff_enfase.iterrows()]
                onoff_print(f'flag_enfase = {flag_enfase}\n\n')

                # Quando uma disciplina da lista de ok é computada em certa ênfase,
                # retiramos da lista para não correr o risco de contar 2 vezes.
                disciplinas_ok = [item for item in disciplinas_ok if item not in dff_enfase[flag_enfase].index]

                ch_enfase = sum(dff_enfase.loc[flag_enfase, 'CH'])
                onoff_print(f'Antes ch_enfase = {ch_enfase}\n\n')

                if ch_enfase > 8*15:
                    ch_enfase = 8*15
                onoff_print(f'Depois ch_enfase = {ch_enfase}\n\n')

                ch_cursada += ch_enfase
                onoff_print(f'ch_cursada = {ch_cursada}\n\n')
                onoff_print('=====\n\n')

            ch_restante = (CH_optativa - ch_cursada) if (CH_optativa - ch_cursada) > 0 else 0
            perc_restante = 100*ch_restante/CH_optativa
            perc_cursada = 100 - perc_restante
        else:
            ch_cursada = sum(dff.loc[flag_cursada, 'CH'])
            ch_total = sum(dff['CH'])
            ch_restante = ch_total - ch_cursada
            perc_restante = 100*ch_restante/ch_total
            perc_cursada = 100*ch_cursada/ch_total

        aux.append(
            {
                'Tipo': item,
                'CH_cursada': ch_cursada, 
                '%_cursada': f'{perc_cursada:.2f}', 
                'CH_restante': ch_restante, 
                '%_restante': f'{perc_restante:.2f}', 
            }
        )

        if 'Extensão' in dff.columns:
            aux[-1]['Extensão'] = f"{sum(dff.loc[flag_cursada, 'Extensão'])} de {sum(dff['Extensão'])}"

    return pd.DataFrame(aux, index=minha_ordem_periodos)

def obter_lista_de_disciplinas_para_dispensa(df12, df1, df2):

    onoff_print(f'obter_lista_de_disciplinas_para_dispensa:')

    ret1 = []
    ret2 = []
    for idx, row in df12.iterrows():

            # obtém ocorrências de "idx" em df_eqv...
            d1 = [item.strip() for item in row['Disciplina_1'].split('&&')]
            d2 = [item.strip() for item in row['Disciplina_2'].split('&&')]

            ch1 = [df1.loc[item, 'CH'] for item in d1]
            ch2 = [df2.loc[item, 'CH'] for item in d2]

            if sum(ch1) < sum(ch2):
                aux = [item for item in d1 if item not in ret1]
                ret1.extend(aux)
                aux = [item for item in d2 if item not in ret2]
                ret2.extend(aux)

    return ret1, ret2

# ==============================================================================
# Dicionário de Engenharia Elétrica - UFPB
# ==============================================================================

dict_config = {
    'document_title': 'PPC DEE',
    'dashboard_title': '''
        ### Simulador de migração de PPC - DEE/CEAR
        Versão 0.2 - 07/07/2023 - Desenvolvimento: CEARDados
    ''',
    # Versão 0.0 - 05/04/2023 - Desenvolvimento: CEARDados
    # Versão 0.1 - 08/05/2023 - Desenvolvimento: CEARDados
    'input_filename': './dados/Tabela de Equivalências_DEE.xlsx',
    'enfases_ppc_1': {
        'GEN': {
            'nome': 'Generalista',
            'planilha': 'PPC Anterior GEN',
        },
        'ELE': {
            'nome': 'Eletrônica',
            'planilha': 'PPC Anterior ELE',
        },
        'C&A': {
            'nome': 'Controle e Automação',
            'planilha': 'PPC Anterior C&A',
        },
        'SDE': {
            'nome': 'Sistemas de Energia',
            'planilha': 'PPC Anterior SDE',
        },
    },
    'enfases_ppc_2': {
        'SIN': {
            'nome': 'Sistemas Industriais',
            'planilha': 'PPC Atual SIN',
        },
        'SDE': {
            'nome': 'Sistemas de Energia',
            'planilha': 'PPC Atual SDE',
        },
    },
    'planilha_eqv_ppc_1_e_ppc_2': 'Equivalências',
    'ordem_periodos': [
        '1° período', 
        '2° período', 
        '3° período', 
        '4° período', 
        '5° período',
        '6° período', 
        '7° período', 
        '8° período', 
        '9° período', 
        '10° período',
        'Optativas',
    ],
}


# ==============================================================================
# Dash App - Criação e leitura do arquivo de entrada
# ==============================================================================

dados = pd.read_excel(dict_config['input_filename'], None)
app = Dash(__name__, title=dict_config['document_title'])
server = app.server

# ==============================================================================
# Dash App - Layout
# ==============================================================================

app.layout = html.Div(
    [
        html.Div(
            children=[
                dcc.Markdown(
                    children=[dict_config['dashboard_title']],
                    className="twelve columns column_style",
                ),
            ],
            className="row row_style",
        ),
        html.Div(
            children=[
                html.Div(
                    children=[
                        html.H6('Disciplinas do PPC Anterior'),
                        dcc.Dropdown(
                            id="dropdown_ppc_1", 
                            options=[
                                {'label': f"{key} - {value['nome']}", 'value': key} 
                                for key, value in dict_config['enfases_ppc_1'].items()
                            ], 
                            placeholder="Selecione uma ênfase...",
                            value=list(dict_config['enfases_ppc_1'].keys())[0],
                        ),
                    ],
                    className="six columns column_style_sem_center zera_margin-left",
                ),
                html.Div(
                    children=[
                        html.H6('Disciplinas do PPC Atual'),
                        dcc.Dropdown(
                            id="dropdown_ppc_2", 
                            options=[
                                {'label': f"{key} - {value['nome']}", 'value': key} 
                                for key, value in dict_config['enfases_ppc_2'].items()
                            ], 
                            placeholder="Selecione uma ênfase...",
                            value=list(dict_config['enfases_ppc_2'].keys())[0],
                        ),
                    ],
                    className="six columns column_style_sem_center",
                ),
                html.Div(
                    children=[
                        dcc.Checklist(
                            id=f'checklist_marcar_todas',
                            options=[{'label': 'Marcar todas.', 'value': 'Marcar todas.'}],
                            value=[],
                        ),
                        html.Hr(),
                        dcc.Checklist(id=f'checklist_ppc_1'),
                        html.Hr(),
                        html.B('* Significa que será preciso abrir processo de dispensa.'),
                    ],
                    className="six columns column_style_sem_center zera_margin-left",
                ),
                html.Div(
                    children=[dcc.Checklist(id=f'checklist_ppc_2')],
                    className="six columns column_style_sem_center",
                ),
            ],
            className="row row_style",
        ),
        html.Div(
            children=[
                html.Div(
                    id='div_resumo_ppc_1',
                    className="six columns column_style_sem_center zera_margin-left",
                ),
                html.Div(
                    id='div_resumo_ppc_2',
                    className="six columns column_style_sem_center",
                ),
            ],
            className="row row_style",
        ),
    ]
)

# ==============================================================================
# Dash App - Callbacks
# ==============================================================================

@app.callback(
    Output('checklist_ppc_1', 'options'),
    Output('checklist_ppc_2', 'options'),
    Input('dropdown_ppc_1', 'value'),
    Input('dropdown_ppc_2', 'value'),
)
def gera_checklists(dropdown_ppc_1, dropdown_ppc_2):

    if dropdown_ppc_1 is None:
        raise PreventUpdate

    onoff_print(f'gera_checklists:')
    onoff_print(f'dropdown_ppc_1 = {dropdown_ppc_1}')
    onoff_print(f'dropdown_ppc_2 = {dropdown_ppc_2}')

    # Com base nas escolhas de ênfases, lê df's de interesse.
    df1, df2, df_eqv, disc_com_aumento_1, disc_com_aumento_2 = \
        acessar_dados_de_entrada(
            dados, 
            dict_config['enfases_ppc_1'][dropdown_ppc_1]['planilha'], 
            dict_config['enfases_ppc_2'][dropdown_ppc_2]['planilha'], 
            dict_config['planilha_eqv_ppc_1_e_ppc_2'], 
        )

    # Com os df's na memória, carrega as checklists.
    options_ppc_1 = [
        {
            'label': html.B(f'{periodo} - {disciplina} - {creditos} créditos*'), 
            'value': disciplina
        }
        if disciplina in disc_com_aumento_1
        else
        {
            'label': f'{periodo} - {disciplina} - {creditos} créditos', 
            'value': disciplina
        }
        for periodo, disciplina, creditos in zip(df1['Período'], df1.index, df1['Créditos'])
    ]

    options_ppc_2 = [
        {
            'label': html.B(f'{periodo} - {disciplina} - {creditos} créditos*'), 
            'value': disciplina,
            'disabled': True,
        }
        if disciplina in disc_com_aumento_2
        else
        {
            'label': f'{periodo} - {disciplina} - {creditos} créditos', 
            'value': disciplina,
            'disabled': True,
        }
        for periodo, disciplina, creditos in zip(df2['Período'], df2.index, df2['Créditos'])
    ]

    onoff_print(f'options_ppc_1 = {options_ppc_1}\n')
    onoff_print(f'options_ppc_2 = {options_ppc_2}\n')
    onoff_print(f'=====\n\n')

    return options_ppc_1, options_ppc_2



@app.callback(
    Output('checklist_ppc_1', 'value'),
    Input('checklist_marcar_todas', 'value'),
    State('checklist_ppc_1', 'options'),
)
def marcar_desmarcar_todas(values, options):

    if values is None:
        raise PreventUpdate

    onoff_print(f'marcar_desmarcar_todas:')
    onoff_print(f'values = {values}')
    onoff_print(f'options = {options}')

    return [] if len(values) == 0 else [item['value'] for item in options]



@app.callback(
    Output('checklist_ppc_2', 'value'),
    Output('div_resumo_ppc_1', 'children'),
    Output('div_resumo_ppc_2', 'children'),
    Input('checklist_ppc_1', 'value'),
    State('dropdown_ppc_1', 'value'),
    State('dropdown_ppc_2', 'value'),
)
def gera_checklist_ppc_2_e_graficos(checklist_values, dropdown_ppc_1, dropdown_ppc_2):

    if checklist_values is None:
        raise PreventUpdate

    onoff_print(f'gera_markdown_de_todas_as_categorias:')
    onoff_print(f'checklist_values = {checklist_values}')
    onoff_print(f'dropdown_ppc_1 = {dropdown_ppc_1}')
    onoff_print(f'dropdown_ppc_2 = {dropdown_ppc_2}')

    # Com base nas escolhas de ênfases, lê df's de interesse.
    df1, df2, df_eqv, disc_com_aumento_1, disc_com_aumento_2 = \
        acessar_dados_de_entrada(
            dados, 
            dict_config['enfases_ppc_1'][dropdown_ppc_1]['planilha'], 
            dict_config['enfases_ppc_2'][dropdown_ppc_2]['planilha'], 
            dict_config['planilha_eqv_ppc_1_e_ppc_2'], 
        )

    # Percorrer equivalencias em busca de match...
    list_match = []
    for _, row_eqv in df_eqv.iterrows():

        # Pegar disciplinas no ppc_1
        d1 = row_eqv['Disciplina_1'].split('&&')
        d1 = [item.strip() for item in d1]

        # Se todos os elementos de d1 estiverem marcados, ocorre um match!
        list_d1_ok = [(disciplina in checklist_values) for disciplina in d1]

        # depuração
        onoff_print(f'd1 = {d1}\n')
        onoff_print(f'list_d1_ok = {list_d1_ok}\n')

        if all(list_d1_ok):

            # Pegar disciplinas no ppc_2
            d2 = row_eqv['Disciplina_2'].split('&&')
            d2 = [item.strip() for item in d2]

            # depuração
            onoff_print(f'd1 = {d1}\n')
            onoff_print(f'list_d1_ok = {list_d1_ok}\n')
            onoff_print(f'd2 = {d2}\n')

            # Percorrer disciplinas de d2...
            for disciplina in d2:

                # Localizar no ppc_2 
                row_ppc_2 = df2.loc[disciplina]
                onoff_print(f'row_ppc_2 = \n{row_ppc_2}\n')

                # Pegar (periodo, credito e extensão), mas evitando duplicidades...
                jah_dispensou = [(disciplina == item) for item in list_match]
                if any(jah_dispensou):
                    continue

                # Chegando aqui... "Dispensar disciplina"
                list_match.append(disciplina)

    # Construir os resumos

    # Existe um único caso que saiu da lógica usual: Generalista de Elétrica.
    # Ele precisa de 20 créditos de Optativas, mas limitado a 8 por ênfase...
    # Para esse caso extraordinário, foi desenvolvida uma rotina própria.
    if dict_config['document_title'] == 'PPC DEE' and dropdown_ppc_1 == 'GEN':
        resumo_ppc_1 = montar_resumo_ppc_dee_ufpb_generalista(df1, checklist_values, 20*15, dict_config['ordem_periodos'])
    else:
        resumo_ppc_1 = montar_resumo_ppc(df1, checklist_values, 20*15, dict_config['ordem_periodos'])

    resumo_ppc_2 = montar_resumo_ppc(df2, list_match, 20*15, dict_config['ordem_periodos'])

    # Construir as tabelas
    cursada = sum(resumo_ppc_1['CH_cursada'])
    restante = sum(resumo_ppc_1['CH_restante'])

    fig1 = go.Figure(
        data=[
            go.Bar(name='Cursada', x=resumo_ppc_1['Tipo'], y=resumo_ppc_1['CH_cursada']),
            go.Bar(name='Restante', x=resumo_ppc_1['Tipo'], y=resumo_ppc_1['CH_restante']),
        ]
    )
    fig1.update_layout(barmode='stack')
    fig1.update_layout(title_text=f"{cursada}h / {restante}h")
    fig1.update_layout(legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))

    ret_1 = [
        html.H6('Resumo PPC Anterior (CH 3855h):'),
        # html.P(f"Carga horária: {cursada}h cursadas, {restante}h restantes"),
        # html.P(f"Créditos: {cursada/15:.0f} cursados, {restante/15:.0f} restantes"),
        dcc.Graph(
            figure=fig1,
        ),
        dash_table.DataTable(
            data = resumo_ppc_1.to_dict('records'),
            columns = [{"name": i, "id": i} for i in resumo_ppc_1.columns],
            style_table={'overflowX': 'auto'},
            style_as_list_view=True,
            style_cell={'textAlign': 'center'},
        ),
    ]

    cursada = sum(resumo_ppc_2['CH_cursada'])
    restante = sum(resumo_ppc_2['CH_restante'])

    fig2 = go.Figure(
        data=[
            go.Bar(name='Cursada', x=resumo_ppc_2['Tipo'], y=resumo_ppc_2['CH_cursada']),
            go.Bar(name='Restante', x=resumo_ppc_2['Tipo'], y=resumo_ppc_2['CH_restante']),
        ]
    )
    fig2.update_layout(barmode='stack')
    fig2.update_layout(title_text=f"{cursada}h / {restante}h")
    fig2.update_layout(legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))

    ret_2 = [
        html.H6('Resumo PPC Atual (CH 3900h):'),
        # html.P(f"Carga horária: {cursada}h dispensadas, {restante}h restantes"),
        # html.P(f"Créditos: {cursada/15:.0f} dispensados, {restante/15:.0f} restantes"),
        dcc.Graph(
            figure=fig2,
        ),
        dash_table.DataTable(
            data = resumo_ppc_2.to_dict('records'),
            columns = [{"name": i, "id": i} for i in resumo_ppc_2.columns],
            style_table={'overflowX': 'auto'},
            style_as_list_view=True,
            style_cell={'textAlign': 'center'},
        ),
    ]

    return list_match, ret_1, ret_2



if __name__ == '__main__':
    app.run_server(debug=ehDebug, port=8050)
