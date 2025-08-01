import os
import google.generativeai as genai
from flask import Flask, render_template, request, jsonify
import json
from datetime import datetime

app = Flask(__name__)

# Gemini APIの設定
genai.configure(api_key=os.environ.get('GEMINI_API_KEY'))
model = genai.GenerativeModel('gemini-1.5-flash')

# ゲーム状態を保存
game_state = {
    'used_words': [],
    'last_word': '',
    'game_over': False,
    'winner': None,
    'history': []
}

def reset_game():
    """ゲームをリセット"""
    global game_state
    game_state = {
        'used_words': [],
        'last_word': '',
        'game_over': False,
        'winner': None,
        'history': []
    }

def check_word_validity(word, last_word):
    """単語の有効性をチェック"""
    if not word:
        return False, "単語が入力されていません"
    
    # 既に使用された単語かチェック
    if word in game_state['used_words']:
        return False, f"「{word}」は既に使用されています"
    
    # 最後の文字と最初の文字が一致するかチェック
    if last_word and word[0] != last_word[-1]:
        return False, f"「{last_word}」の最後の文字「{last_word[-1]}」で始まる単語を入力してください"
    
    # 「ん」で終わるかチェック
    if word.endswith('ん'):
        return False, f"「{word}」は「ん」で終わっているので負けです"
    
    return True, "有効な単語です"

def get_ai_response(user_word):
    """AIからしりとりの返答を取得"""
    try:
        # プロンプトを作成
        used_words_str = "、".join(game_state['used_words']) if game_state['used_words'] else "なし"
        
        prompt = f"""
あなたはしりとりゲームをしています。以下のルールを厳密に守ってください：

1. 「{user_word}」の最後の文字「{user_word[-1]}」で始まる日本語の単語を1つだけ答えてください
2. 「ん」で終わる単語は絶対に使わないでください
3. 既に使用された単語は使わないでください
4. 単語のみを回答し、説明は不要です

既に使用された単語: {used_words_str}

回答する単語:
"""
        
        print(f"DEBUG: プロンプト送信中... ユーザー単語: {user_word}")
        print(f"DEBUG: API Key設定確認: {'設定済み' if os.environ.get('GEMINI_API_KEY') else '未設定'}")
        
        response = model.generate_content(prompt)
        print(f"DEBUG: API応答受信: {response}")
        print(f"DEBUG: 応答テキスト: '{response.text}'")
        
        ai_word = response.text.strip()
        print(f"DEBUG: 処理後のAI単語: '{ai_word}'")
        
        # AIの回答をチェック
        is_valid, message = check_word_validity(ai_word, user_word)
        print(f"DEBUG: 単語有効性チェック: {is_valid}, メッセージ: {message}")
        
        if not is_valid:
            # AIが無効な単語を返した場合、AIの負け
            game_state['game_over'] = True
            game_state['winner'] = 'user'
            return ai_word, f"AIが無効な単語「{ai_word}」を返しました。あなたの勝ちです！"
        
        return ai_word, "有効な単語です"
        
    except Exception as e:
        print(f"DEBUG: エラー発生: {type(e).__name__}: {str(e)}")
        import traceback
        print(f"DEBUG: トレースバック: {traceback.format_exc()}")
        game_state['game_over'] = True
        game_state['winner'] = 'user'
        return "", f"AIでエラーが発生しました: {str(e)}"

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/start_game', methods=['POST'])
def start_game():
    """新しいゲームを開始"""
    reset_game()
    return jsonify({
        'status': 'success',
        'message': 'ゲームを開始しました！最初の単語を入力してください。'
    })

@app.route('/play', methods=['POST'])
def play():
    """しりとりをプレイ"""
    data = request.json
    user_word = data.get('word', '').strip()
    
    if game_state['game_over']:
        return jsonify({
            'status': 'error',
            'message': 'ゲームは終了しています。新しいゲームを開始してください。'
        })
    
    # ユーザーの単語をチェック
    is_valid, message = check_word_validity(user_word, game_state['last_word'])
    
    if not is_valid:
        game_state['game_over'] = True
        game_state['winner'] = 'ai'
        game_state['history'].append({
            'type': 'user',
            'word': user_word,
            'timestamp': datetime.now().isoformat(),
            'valid': False,
            'message': message
        })
        
        return jsonify({
            'status': 'game_over',
            'winner': 'ai',
            'message': message,
            'history': game_state['history']
        })
    
    # ユーザーの単語を記録
    game_state['used_words'].append(user_word)
    game_state['last_word'] = user_word
    game_state['history'].append({
        'type': 'user',
        'word': user_word,
        'timestamp': datetime.now().isoformat(),
        'valid': True,
        'message': '有効な単語です'
    })
    
    # AIの返答を取得
    ai_word, ai_message = get_ai_response(user_word)
    
    if game_state['game_over']:
        game_state['history'].append({
            'type': 'ai',
            'word': ai_word,
            'timestamp': datetime.now().isoformat(),
            'valid': False,
            'message': ai_message
        })
        
        return jsonify({
            'status': 'game_over',
            'winner': game_state['winner'],
            'message': ai_message,
            'ai_word': ai_word,
            'history': game_state['history']
        })
    
    # AIの単語を記録
    game_state['used_words'].append(ai_word)
    game_state['last_word'] = ai_word
    game_state['history'].append({
        'type': 'ai',
        'word': ai_word,
        'timestamp': datetime.now().isoformat(),
        'valid': True,
        'message': '有効な単語です'
    })
    
    return jsonify({
        'status': 'continue',
        'ai_word': ai_word,
        'message': f'AIの返答: {ai_word}',
        'next_char': ai_word[-1],
        'history': game_state['history']
    })

@app.route('/game_status')
def game_status():
    """現在のゲーム状態を取得"""
    return jsonify({
        'game_over': game_state['game_over'],
        'winner': game_state['winner'],
        'used_words': game_state['used_words'],
        'last_word': game_state['last_word'],
        'history': game_state['history']
    })

if __name__ == '__main__':
    # 本番環境対応
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
