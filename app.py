from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_from_directory
from werkzeug.utils import secure_filename
import requests
import os
import json
import time


# Carregar variáveis de ambiente do arquivo .env



# Variáveis Globais e Configurações



IDS_FILE = os.getenv('IDS_FILE', 'ids.json')  # Padrão: ids.json
ACCESS_TOKEN = os.getenv('ACCESS_TOKEN')
CONTA_PRINCIPAL = os.getenv('CONTA_PRINCIPAL')
ROYAL_X = os.getenv('ROYAL_X')
EMPREENDEDOR_DO_FUTURO = os.getenv('EMPREENDEDOR_DO_FUTURO')

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY')

created_media_records = []

# Helper Functions
def load_ids():
    """Load saved IDs from the JSON file."""
    if os.path.exists(IDS_FILE):
        with open(IDS_FILE, "r") as file:
            return json.load(file)
    return []

def save_ids(ids):
    """Save IDs to the JSON file."""
    with open(IDS_FILE, "w") as file:
        json.dump(ids, file)

def clear_ids():
    """Clear the JSON file."""
    if os.path.exists(IDS_FILE):
        os.remove(IDS_FILE)

def retry_request(url, data, max_retries=3, delay=2):
    """Retry HTTP POST requests on transient errors."""
    for attempt in range(max_retries):
        response = requests.post(url, data=data)
        if response.status_code == 200:
            return response
        app.logger.warning(f"Tentativa {attempt + 1} falhou: {response.text}")
        time.sleep(delay)
    return response

def get_account_id(account_name):
    """Map account name to account ID."""
    return {
        'Principal': CONTA_PRINCIPAL,
        'Royal X': ROYAL_X,
        'Empreendedor Do Futuro': EMPREENDEDOR_DO_FUTURO
    }.get(account_name)
    
def get_account_name(account_id):
    """Map account ID to account name."""
    return {
        '17841401531671783': 'Principal',
        '17841463963815604': 'Royal X',
        '17841470729686161': 'Empreendedor Do Futuro'
    }.get(account_id)
# Routes
@app.route('/', methods=['GET', 'POST'])
def create_media():
    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'create':
            try:
                # Form data
                media_type = request.form['media_type']
                media_url = request.form['media_url']
                caption = request.form['caption']
                hashtags = request.form['hashtags']
                description = request.form['description']
                conta_id = request.form['conta']

                hide_likes = request.form.get('hide_likes') == 'on'
                hide_comments = request.form.get('hide_comments') == 'on'
                full_caption = f"{caption} {hashtags}"

                # Request parameters
                media_params = {
                    'access_token': ACCESS_TOKEN,
                    'caption': full_caption,
                    'hide_likes': hide_likes,
                    'hide_comments': hide_comments
                }

                if media_type == 'image':
                    media_params['image_url'] = media_url
                elif media_type == 'video':
                    media_params['video_url'] = media_url
                    media_params['media_type'] = 'REELS'

                create_url = f'https://graph.facebook.com/v21.0/{conta_id}/media'
                response = requests.post(create_url, params=media_params)

                if response.status_code == 200:
                    creation_id = response.json().get('id')
                    created_media_records.append({
                        'id': creation_id,
                        'conta': request.form['conta'],
                        'type': media_type,
                        'caption': caption,
                        'description': description,
                        'hide_likes': hide_likes,
                        'hide_comments': hide_comments
                    })
                    flash(f'Mídia criada com sucesso! ID: {creation_id}', 'success')
                else:
                    flash(f'Erro ao criar a mídia: {response.json()}', 'danger')
            except Exception as e:
                flash(f'Erro: {str(e)}', 'danger')

        return redirect(url_for('create_media'))

    return render_template('create_media.html', created_media_records=created_media_records)

@app.route('/publish-media/<media_id>/<conta>', methods=['POST'])
def publish_media(media_id, conta):
    account_name = get_account_name(conta)
    if not account_name:
        flash("Conta inválida.", "danger")
        return redirect(url_for('create_media'))

    publish_url = f'https://graph.facebook.com/v21.0/{conta}/media_publish'
    response = requests.post(publish_url, params={
        'creation_id': media_id,
        'access_token': ACCESS_TOKEN
    })

    if response.status_code == 200:
        flash(f'Publicadas com sucesso!', 'success')
    else:
        flash(f'Erro ao publicar mídia {media_id}: {response.json()}', 'danger')

    return redirect(url_for('create_media'))


@app.route('/publish-all', methods=['POST'])
def publish_all_media():
    errors = []
    for media in created_media_records:
        try:
            publish_media(media['id'], media['conta'])
        except Exception as e:
            errors.append(f"Erro ao publicar {media['id']}: {str(e)}")

    if errors:
        for error in errors:
            flash(error, 'danger')
    else:
        flash("Todas as mídias foram publicadas com sucesso!", "success")
    return redirect(url_for('create_media'))


@app.route('/delete-media/<media_id>', methods=['POST'])
def delete_media(media_id):
    global created_media_records
    created_media_records = [m for m in created_media_records if m['id'] != media_id]
    flash(f'Mídia {media_id} excluída com sucesso.', 'success')
    return redirect(url_for('create_media'))

@app.route('/carrocel', methods=['GET', 'POST'])
def carrocel():
    media_ids = load_ids()
    return render_template('carrocel.html', created_media_records=media_ids)

@app.route('/carrocel/add_image', methods=['POST'])
def add_image():
    media_ids = load_ids()
    media_url = request.form['media_url']
    description = request.form.get('description', '')
    media_type = request.form.get('type', '')
    conta = request.form.get('conta', '')

    if media_type not in ['image', 'video']:
        flash("Tipo de mídia inválido.", "danger")
        return redirect(url_for('carrocel'))

    conta_id = get_account_id(conta)
    if not conta_id:
        flash("Conta não reconhecida.", "danger")
        return redirect(url_for('carrocel'))

    create_url = f'https://graph.facebook.com/v21.0/{conta_id}/media'
    response = requests.post(create_url, data={
        'access_token': ACCESS_TOKEN,
        'is_carousel_item': 'true',
        'image_url' if media_type == 'image' else 'video_url': media_url
    })

    if response.status_code == 200:
        media_ids.append({
            'id': response.json().get('id'),
            'conta': conta,
            'description': description,
            'type': media_type
        })
        save_ids(media_ids)
        flash("Mídia adicionada ao carrossel com sucesso!", "success")
    else:
        flash(f"Erro ao adicionar mídia: {response.text}", "danger")

    return redirect(url_for('carrocel'))

@app.route('/carrocel/clear_ids', methods=['POST'])
def clear_all_ids():
    clear_ids()
    flash("IDs limpos com sucesso!", "success")
    return redirect(url_for('carrocel'))

@app.route('/carrocel/create', methods=['POST'])
def create_carousel():
    media_ids = load_ids()
    conta = request.form.get('conta')
    caption = request.form['caption']
    hashtags = request.form['hashtags']

    conta_id = get_account_id(conta)
    if not conta_id:
        flash("Conta inválida.", "danger")
        return redirect(url_for('carrocel'))

    filtered_media = [m['id'] for m in media_ids if m['conta'] == conta]
    if not filtered_media:
        flash("Nenhuma mídia foi adicionada para esta conta.", "danger")
        return redirect(url_for('carrocel'))

    response = retry_request(f'https://graph.facebook.com/v21.0/{conta_id}/media', {
        'access_token': ACCESS_TOKEN,
        'caption': f"{caption} {hashtags}",
        'media_type': 'CAROUSEL',
        'children': ",".join(filtered_media)
    })

    if response.status_code == 200:
        flash("Carrossel criado e publicado com sucesso!", "success")
        clear_ids()
    else:
        flash(f"Erro ao criar carrossel: {response.text}", "danger")

    return redirect(url_for('carrocel'))

# Main Function
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)