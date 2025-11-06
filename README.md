# ☀️ Sol à Vista: Gerador de Lista de Materiais Fotovoltaicos

Este é um sistema web leve e dinâmico, desenvolvido em **Flask (Python)**, projetado para simplificar e agilizar a criação e o gerenciamento de listas de materiais para projetos de energia solar fotovoltaica.

Com uma interface responsiva e intuitiva nas cores verde e laranja (simbolizando natureza e energia), a ferramenta permite que o responsável técnico gere rapidamente documentos em PDF com a lista exata de componentes necessários, salvando o histórico e facilitando o compartilhamento.

## ✨ Funcionalidades Principais

* **Geração de PDF Rápida:** Crie listas de materiais formatadas e profissionais instantaneamente, prontas para impressão ou envio.
* **Gestão de Histórico:** Todas as listas geradas são salvas com informações do cliente, técnico e data, facilitando a consulta e download posterior.
* **Materiais Dinâmicos:** Selecione materiais de categorias pré-definidas (via *dropdown*) ou adicione novos itens customizados diretamente no formulário.
* **Design Responsivo:** Interface adaptável a celulares, tablets e desktops (Mobile-First Design), utilizando uma paleta de cores vibrante (Laranja & Verde).
* **Integração com WhatsApp:** Link direto para compartilhamento rápido da notificação de lista pronta via WhatsApp.
* **Persistência de Dados:** Uso de SQLite para armazenamento de registros de forma leve.

## 🛠️ Tecnologias Utilizadas

* **Backend:** Python 3.x
* **Framework Web:** Flask
* **Banco de Dados:** SQLite3 (Para histórico e persistência)
* **Geração de Documentos:** ReportLab (Python Library para criação de PDF)
* **Frontend:** HTML5, CSS3 (Design Responsivo), JavaScript
* **Design:** Paleta de cores Laranja (`#FF8C42`) e Verde (`#4CAF50`).
