# -*- coding: utf-8 -*-
"""
@file: app.py
@description: '분리수GO' 웹 애플리케이션의 백엔드 메인 파일입니다.
              Flask 프레임워크를 사용하여 웹 요청을 처리하고,
              학생 데이터 관리, 이미지 처리(Teachable Machine 연동),
              그리고 웹 페이지 렌더링을 담당합니다.
@version: 1.0.0
@date: 2025-06-08
@author: 오산고 이현서

@changes:
  - 1.0.0 (2025-06-08): 초기 버전. 기본 라우팅, 데이터 관리, 이미지 처리 임시 로직 구현.
                       Teachable Machine 연동을 위한 기본 구조 및 주석 추가.
"""

# 라이브러리 설치 방법:
# 이 프로젝트는 Python의 Flask 웹 프레임워크와 requests 라이브러리를 사용합니다.
# 프로젝트 루트 디렉토리에서 다음 명령어를 실행하여 필요한 라이브러리를 설치할 수 있습니다.
# pip install -r requirements.txt
# (requirements.txt 파일에는 Flask와 requests가 명시되어 있습니다.)

from flask import Flask, render_template, request, jsonify, redirect, url_for
import json
from datetime import datetime
import base64
import requests # Teachable Machine API 호출용 (이미지 분석 요청 시 사용)
from pyngrok import ngrok, conf # ngrok 터널링을 위한 라이브러리

# Flask 애플리케이션 초기화
app = Flask(__name__)

# ngrok 인증 토큰 설정 (YOUR_NGROK_AUTH_TOKEN 부분을 본인의 ngrok 토큰으로 변경해주세요!)
# ngrok 토큰은 https://dashboard.ngrok.com/get-started/your-authtoken 에서 확인할 수 있습니다.
conf.get_default().auth_token = "2yDZOZvEgC8sgOXvcJWFZOcsadd_7mKdrnmpfcuKAsgKtJnZM" # 이 줄의 주석을 해제하고 토큰을 입력하세요.
# ngrok.set_auth_token("YOUR_NGROK_AUTH_TOKEN") # 또는 이 함수를 직접 호출해도 됩니다.
# (주의: 이 토큰은 외부에 노출되지 않도록 주의해야 합니다.)

# 데이터 파일 경로 정의
# 학생들의 학번과 점수 정보를 저장하는 JSON 파일입니다.
DATA_FILE = 'data.json'

# Teachable Machine 모델 URL 정의
# 사용자가 학습시킨 Teachable Machine 모델의 URL입니다.
# 실제 이미지 분석 요청 시 이 URL을 사용하여 모델에 접근합니다.
# 현재는 임시 URL이며, 실제 모델의 API 엔드포인트로 변경해야 합니다.
TEACHABLE_MACHINE_MODEL_URL = "https://teachablemachine.withgoogle.com/models/Q8z_07lsS/" # 실제 모델 URL로 변경 필요

# @function: load_data
# @description: DATA_FILE에 저장된 학생 데이터를 로드합니다.
#               파일이 없거나 JSON 형식이 올바르지 않을 경우 빈 리스트를 반환합니다.
# @param: None
# @returns: list - 로드된 학생 데이터 리스트
def load_data():
    try:
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        # 파일이 없거나 JSON 디코딩 오류 발생 시 빈 리스트 반환
        return []

# @function: save_data
# @description: 주어진 학생 데이터를 DATA_FILE에 JSON 형식으로 저장합니다.
# @param: data (list) - 저장할 학생 데이터 리스트
# @returns: None
def save_data(data):
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False) # 한글 깨짐 방지

# @route: /
# @description: 웹 애플리케이션의 초기 화면(메인 페이지)을 렌더링합니다.
#               현재 상위 3명의 랭킹 정보를 로드하여 템플릿에 전달합니다.
# @methods: GET
# @returns: rendered_template - 'index.html' 페이지
@app.route('/')
def index():
    students_data = load_data()
    # 점수를 기준으로 학생 데이터를 내림차순 정렬하여 랭킹을 계산합니다.
    ranking = sorted(students_data, key=lambda x: x['score'], reverse=True)
    # 상위 3명의 학생만 랭킹으로 표시합니다.
    top_3_ranking = ranking[:3]
    
    # 현재 로그인한 학생의 랭킹은 JavaScript를 통해 클라이언트 측에서 처리될 예정입니다.
    return render_template('index.html', ranking=top_3_ranking)

# @route: /submit_id
# @description: 사용자가 입력한 학번을 처리하고, 해당 학생의 정보를 반환합니다.
#               새로운 학번일 경우 데이터를 추가하고, 기존 학번일 경우 활동 시간을 업데이트합니다.
# @methods: POST
# @returns: json - 학생 정보 (학번, 점수, 랭킹) 또는 오류 메시지
@app.route('/submit_id', methods=['POST'])
def submit_id():
    student_id = request.form.get('student_id')
    # 학번 유효성 검사: 5자리 숫자인지 확인
    if not student_id.isdigit() or len(student_id) != 5:
        return jsonify({'error': '5자리 숫자만 입력 가능합니다'}), 400

    students = load_data()
    # 입력된 학번에 해당하는 학생을 찾습니다.
    student = next((s for s in students if s['student_id'] == student_id), None)
    
    if not student:
        # 새로운 학생일 경우, 초기 점수 0점으로 추가
        student = {'student_id': student_id, 'score': 0, 'last_activity': datetime.now().isoformat()}
        students.append(student)
        save_data(students)
    else:
        # 기존 학생일 경우, 마지막 활동 시간 업데이트
        student['last_activity'] = datetime.now().isoformat()
        save_data(students) 

    # 모든 학생 데이터를 다시 정렬하여 현재 학생의 랭킹을 계산합니다.
    sorted_students = sorted(students, key=lambda x: x['score'], reverse=True)
    current_rank = next((i + 1 for i, s in enumerate(sorted_students) if s['student_id'] == student_id), len(sorted_students) + 1)
    
    return jsonify({
        'student_id': student_id,
        'score': student['score'],
        'rank': current_rank
    })

# @route: /camera
# @description: 카메라 촬영 페이지를 렌더링합니다.
#               학번이 유효한지 확인하고, 해당 학생의 현재 점수를 전달합니다.
# @methods: GET
# @returns: rendered_template - 'camera.html' 페이지 또는 메인 페이지로 리다이렉트
@app.route('/camera')
def camera():
    student_id = request.args.get('student_id')
    # 학번이 없으면 메인 페이지로 리다이렉트
    if not student_id:
        return redirect(url_for('index')) 

    students = load_data()
    # 유효한 학번인지 확인
    student = next((s for s in students if s['student_id'] == student_id), None)
    if not student:
        return redirect(url_for('index')) # 유효하지 않은 학번이면 메인으로

    return render_template('camera.html', student_id=student_id, current_score=student['score'])

# @route: /process_image
# @description: 클라이언트로부터 전송된 이미지 데이터를 처리하고, Teachable Machine 모델을 통해 분석합니다.
#               분석 단계(쓰레기 종류 판별 또는 분리수거함 투입 확인)에 따라 다른 로직을 수행합니다.
#               현재는 임시 판별 로직이 적용되어 있습니다.
# @methods: POST
# @returns: json - 이미지 처리 결과 (성공/실패, 메시지, 다음 단계 정보 등)
@app.route('/process_image', methods=['POST'])
def process_image():
    student_id = request.form.get('student_id')
    image_data_url = request.form.get('image') # Base64 인코딩된 이미지 데이터
    step = request.form.get('step') # 'first' (쓰레기 종류) 또는 'second' (분리수거함 투입)

    # 필수 데이터 누락 여부 확인
    if not student_id or not image_data_url or not step:
        return jsonify({'error': '필수 데이터가 누락되었습니다.'}), 400

    # Base64 이미지 데이터를 바이너리 형태로 디코딩
    try:
        header, encoded = image_data_url.split(",", 1)
        image_bytes = base64.b64decode(encoded)
    except Exception as e:
        return jsonify({'error': f'이미지 디코딩 오류: {e}'}), 400

    # --- Teachable Machine API 호출 (실제 구현 필요) ---
    # 이 부분은 Teachable Machine 모델의 API 연동 방식에 따라 달라집니다.
    # 일반적으로는 이미지 파일을 직접 전송하거나, Base64 인코딩된 문자열을 JSON 형태로 전송합니다.
    # 여기서는 requests 라이브러리를 사용한 예시를 주석으로 제공합니다.
    
    # Teachable Machine 모델이 이미지 파일을 직접 받는 경우 예시:
    # files = {'image': ('image.jpg', image_bytes, 'image/jpeg')}
    # response = requests.post(TEACHABLE_MACHINE_MODEL_URL + 'predict', files=files)

    # Teachable Machine 모델이 Base64 문자열을 JSON으로 받는 경우 예시:
    # headers = {'Content-Type': 'application/json'}
    # data = json.dumps({"image": encoded})
    # response = requests.post(TEACHABLE_MACHINE_MODEL_URL + 'predict', headers=headers, data=data)

    # --- 임시 판별 로직 (실제 Teachable Machine 연동 전까지 사용) ---
    # 실제 Teachable Machine 모델 연동 시 이 부분은 모델의 예측 결과로 대체됩니다.
    prediction_result = {"class": "플라스틱", "confidence": 0.95} # 예시 결과
    
    if step == 'first':
        # 1단계: 쓰레기 종류 판별
        # Teachable Machine 결과에서 가장 높은 확률의 클래스(쓰레기 종류) 추출
        predicted_class = prediction_result.get("class", "알 수 없음")
        if predicted_class == "알 수 없음":
            # 인식 실패 시 오류 메시지 반환
            return jsonify({'success': False, 'message': '인식 실패: 쓰레기 종류를 알 수 없습니다.', 'reason': '쓰레기 종류 불분명', 'next_step': '재촬영'}), 200
        # 성공 시 예측된 쓰레기 종류 반환
        return jsonify({'success': True, 'step': 'first', 'predicted_class': predicted_class})
    
    elif step == 'second':
        # 2단계: 올바른 분리수거함 투입 판별
        # 이 부분은 1차 촬영 결과(predictedTrashType)와 2차 촬영 결과를 종합하여 판단해야 합니다.
        # Teachable Machine 모델이 '플라스틱_분리수거함', '종이_분리수거함' 등을 판별한다고 가정합니다.
        # 현재는 임시로 항상 True를 반환하도록 설정되어 있습니다.
        is_correct = True # 임시로 True (실제 로직 필요)
        
        if not is_correct:
            # 잘못된 분리수거함 투입 시 오류 메시지 반환
            return jsonify({'success': False, 'message': '인식 실패: 올바른 분리수거함이 아닙니다.', 'reason': '잘못된 분리수거함 투입', 'next_step': '재촬영'}), 200
        
        # 올바르게 분리수거했을 경우 점수 부여
        students = load_data()
        student = next((s for s in students if s['student_id'] == student_id), None)
        if student:
            student['score'] += 10 # 10점 추가
            student['last_activity'] = datetime.now().isoformat() # 활동 시간 업데이트
            save_data(students) # 변경된 데이터 저장
            # 성공 메시지와 함께 획득 점수 및 새로운 총점 반환
            return jsonify({'success': True, 'step': 'second', 'score_awarded': 10, 'new_score': student['score']})
        else:
            # 학생 정보를 찾을 수 없을 경우, 실패 페이지로 리다이렉트
            return redirect(url_for('result', status='fail', reason='학번 오류: 학생 정보를 찾을 수 없습니다.'))

    # 정의되지 않은 'step' 값에 대한 오류 처리
    return jsonify({'error': '알 수 없는 요청입니다.'}), 400

# @route: /result
# @description: 분리수거 결과 페이지를 렌더링합니다.
#               성공/실패 여부, 획득 점수, 실패 사유 등의 정보를 쿼리 파라미터로 받아 화면에 표시합니다.
# @methods: GET
# @returns: rendered_template - 'result.html' 페이지
@app.route('/result')
def result():
    status = request.args.get('status') # 'success' 또는 'fail'
    score = request.args.get('score')   # 성공 시 획득 점수
    reason = request.args.get('reason') # 실패 시 사유
    student_id = request.args.get('student_id') # 학번 (필요시 활용)

    return render_template('result.html', status=status, score=score, reason=reason, student_id=student_id)

# 애플리케이션 실행 진입점
if __name__ == '__main__':
    # ngrok 터널링 시작
    # Flask 앱이 실행될 포트 (5001)를 ngrok에 전달하여 터널을 생성합니다.
    # ngrok 인증 토큰이 설정되어 있지 않으면 오류가 발생할 수 있습니다.
    try:
        # ngrok.set_auth_token("YOUR_NGROK_AUTH_TOKEN") # 여기에 직접 토큰을 넣을 수도 있습니다.
        public_url = ngrok.connect(addr=5001, proto="http")
        print(f"ngrok 터널이 시작되었습니다. 외부 접속 URL: {public_url}")
        print("이 URL을 모바일 브라우저에 입력하여 접속해주세요.")
    except Exception as e:
        print(f"ngrok 터널 시작 중 오류 발생: {e}")
        print("ngrok 인증 토큰이 올바르게 설정되었는지 확인하거나, ngrok 실행 파일을 다운로드했는지 확인해주세요.")
        print("ngrok 설치 및 인증 토큰 설정 방법은 https://ngrok.com/download 및 https://dashboard.ngrok.com/get-started/your-authtoken 을 참조하세요.")
        # ngrok 실패 시에도 Flask 앱은 로컬에서 실행되도록 합니다.
        public_url = "ngrok 터널 시작 실패. 로컬 IP로 접속해주세요."

    # Flask 애플리케이션 실행
    # debug=True 설정 시 코드 변경 시 서버 자동 재시작 및 상세 오류 메시지 제공
    # host='0.0.0.0' 설정 시 외부 IP에서 접속 가능
    # use_reloader=False 설정 시 Flask의 자동 리로더와 ngrok이 충돌하는 것을 방지
    app.run(debug=True, host='0.0.0.0', port=5001, use_reloader=False)
