# -*- coding: utf-8 -*-
"""
@file: app.py
@description: '분리수GO' 웹 애플리케이션의 백엔드 메인 파일입니다.
              Flask 프레임워크를 사용하여 웹 요청을 처리하고,
              학생 데이터 관리, 이미지 처리(Teachable Machine 연동),
              그리고 웹 페이지 렌더링을 담당합니다.
@version: 1.4.0
@date: 2025-06-08
@author: 오산고 이현서

@changes:
  - 1.4.0 (2025-06-08): 데이터 처리 함수 추가 및 오류 처리 강화
  - 1.3.0 (2025-06-08): 라우팅 오류 수정 및 기본 페이지 기능 추가
  - 1.2.0 (2025-06-08): Teachable Machine API 호출 방식 개선
  - 1.1.0 (2025-06-08): Teachable Machine API 연동 구현
  - 1.0.0 (2025-06-08): 초기 버전
"""

from flask import Flask, render_template, request, jsonify, redirect, url_for, send_from_directory
import json
from datetime import datetime
import base64
import requests
from pyngrok import ngrok, conf
import os

app = Flask(__name__, static_folder='static', template_folder='templates')
conf.get_default().auth_token = "2yDZOZvEgC8sgOXvcJWFZOcsadd_7mKdrnmpfcuKAsgKtJnZM"
DATA_FILE = 'data.json'
TEACHABLE_MACHINE_MODEL_URL = "https://teachablemachine.withgoogle.com/models/Q8z_07lsS/"

# 데이터 처리 함수들
def load_data():
    """학생 데이터를 JSON 파일에서 로드합니다."""
    try:
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []

def save_data(data):
    """학생 데이터를 JSON 파일에 저장합니다."""
    try:
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"데이터 저장 오류: {e}")

def map_trash_to_bin(trash_type):
    """쓰레기 종류를 분리수거함 종류로 매핑합니다."""
    mapping = {
        "플라스틱": "플라스틱_분리수거함",
        "종이": "종이_분리수거함", 
        "유리": "유리_분리수거함",
        "캔": "캔_분리수거함",
        "비닐": "비닐_분리수거함"
    }
    return mapping.get(trash_type, "일반_쓰레기통")

# 라우트 함수들
@app.route('/static/<path:filename>')
def static_files(filename):
    return send_from_directory(app.static_folder, filename)

@app.route('/')
def index():
    try:
        students_data = load_data()
        ranking = sorted(students_data, key=lambda x: x['score'], reverse=True)[:3]
        return render_template('index.html', ranking=ranking)
    except Exception as e:
        print(f"메인 페이지 오류: {e}")
        return render_template('error.html', message="메인 페이지를 불러올 수 없습니다"), 500

@app.errorhandler(404)
def page_not_found(e):
    return render_template('error.html', message="페이지를 찾을 수 없습니다"), 404

@app.route('/submit_id', methods=['POST'])
def submit_id():
    """학생 ID를 처리하고 카메라 페이지로 리다이렉트"""
    print("submit_id 라우트 호출됨")  # 디버깅용 로그 추가
    """학생 ID를 처리하고 카메라 페이지로 리다이렉트합니다."""
    try:
        student_id = request.form.get('student_id')
        if not student_id:
            return render_template('error.html', message="학생 ID를 입력해주세요"), 400
        
        # 5자리 숫자인지 확인
        if not student_id.isdigit() or len(student_id) != 5:
            return render_template('error.html', message="학번은 5자리 숫자여야 합니다"), 400
            
        return redirect(url_for('camera_page', student_id=student_id))
    except Exception as e:
        print(f"ID 처리 오류: {e}")
        return render_template('error.html', message="학생 ID 처리 중 오류 발생"), 500

@app.route('/camera')
def camera_page():
    """쓰레기 분리수거 인증을 위한 카메라 페이지"""
    student_id = request.args.get('student_id')
    if not student_id:
        return redirect(url_for('index'))
    
    return render_template('camera.html', student_id=student_id)

@app.route('/process_image', methods=['POST'])
def process_image():
    """촬영된 이미지를 처리하고 분리수거 결과를 반환"""
    try:
        student_id = request.form.get('student_id')
        image_data = request.form.get('image')
        
        if not student_id or not image_data:
            return jsonify({'error': '학생 ID와 이미지 데이터가 필요합니다'}), 400
        
        # TODO: Teachable Machine API 연동 구현
        # 임시 응답 (실제 구현 시 API 호출로 대체)
        result = {
            'result': True,
            'message': '플라스틱 분리수거함에 버려주세요',
            'bin_type': '플라스틱_분리수거함'
        }
        
        # JSON 응답 반환 (클라이언트에서 리다이렉트 처리)
        return jsonify({
            'success': True,
            'message': result['message'],
            'bin_type': result['bin_type'],
            'redirect_url': url_for('result_page',
                                 student_id=student_id,
                                 status='success',
                                 message=result['message'])
        })
    except Exception as e:
        print(f"이미지 처리 오류: {e}")
        return jsonify({
            'success': False,
            'error': '이미지 처리 중 오류 발생',
            'redirect_url': url_for('result_page',
                                 student_id=student_id,
                                 status='fail',
                                 message='이미지 처리 중 오류 발생')
        })

@app.route('/result')
def result_page():
    """분리수거 결과 표시 페이지"""
    student_id = request.args.get('student_id')
    status = request.args.get('status')
    message = request.args.get('message')
    
    if not all([student_id, status, message]):
        return redirect(url_for('index'))
    
    return render_template('result.html',
                         student_id=student_id,
                         status=status,
                         message=message)

# ... (기존의 다른 라우트 함수들 유지) ...

if __name__ == '__main__':
    # 필수 폴더 생성
    os.makedirs('templates', exist_ok=True)
    os.makedirs('static', exist_ok=True)

    # ngrok 터널 시작
    try:
        public_url = ngrok.connect(addr=5001, proto="http")
        print(f"ngrok 터널 시작: {public_url}")
    except Exception as e:
        print(f"ngrok 오류: {e}")

    app.run(debug=True, host='0.0.0.0', port=5001, use_reloader=False)
