[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg?style=for-the-badge)](https://github.com/hacs/integration)

# Kocom Samrt Home
코콤 스마트홈+ 사용자를 위한 홈 어시스턴트 통합.

## 기여

코콤 스마트홈에 문제가 있나요? [Issues](https://github.com/lunDreame/kocom_smart_home/issues) 탭을 열어 작성해 주세요

- 베타 버전으로, 현재는 소수의 사용자를 대상으로 통합을 제공합니다.
- 더 좋은 아이디어가 있나요? [Pull requests](https://github.com/lunDreame/kocom_smart_home/pulls) 열어 등록해 주세요.

이 통합이 당신에게 도움이 되셨나요? [카카오페이](https://qr.kakaopay.com/FWDWOBBmR)

## 설치

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=lunDreame&repository=kocom_smart_home&category=Integration)

이 통합을 설치하려면 이 GitHub Repo를 HACS Custom Reposities에 추가하거나 위의 배지를 클릭하세요.

### 준비

- 월패드에 등록할 휴대전화 번호 (하이픈 없이 11자리)
- 월패드 인증 번호 (8자리)
  - 월패드 모델에 따라 인증 절차가 다를 수 있습니다. DWP-1000KC 모델을 기준으로 하여 부가 기능 메뉴에서 휴대전화 연결 및 인증번호를 받아주세요.
  - 인증은 200초 이내에 완료되어야 합니다.

- 만약 코콤 스마트홈+ 앱에 이미 해당 전화번호가 등록되어 있다면 월패드 인증을 생략할 수 있습니다.

## 기능

| 기기          | 지원              |
| ------------- | ----------------- |         
| 조명          |          O        |
| 콘센트        |          O        |         
| 난방          |          O        |      
| 에어컨        |          O        |        
| 에너지        |          O        |          

- 현재 각 기기의 조회 간격을 설정할 수 있는 기능은 지원되지 않습니다. 이 기능은 향후 업데이트될 예정입니다.
- 사용자의 환경에 따라 지원 항목 및 사용 여부가 다를 수 있습니다.

## 디버깅

문제 파악을 위해 아래 코드를 configuration.yaml 파일에 복사하여 붙여 넣은 후 HomeAssistant를 재시작해 주세요.

그다음, 코콤 스마트홈 구성요소의 디버그 로깅을 활성화하고 생성된 파일을 전송해 주세요.

```
logger:
  default: info
  logs:
    custom_components.kocom_smart_home: debug
```
