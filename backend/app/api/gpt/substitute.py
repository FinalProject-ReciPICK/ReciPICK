from fastapi import APIRouter
from pydantic import BaseModel
from openai import AsyncOpenAI
import os
from dotenv import load_dotenv
import json
import re
import asyncio

load_dotenv()
client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
router = APIRouter()

class SubstituteRequest(BaseModel):
    ingredients: list[str]
    steps: list[str]
    substitutes: list[str]
    serving: str = ""

def build_prompt(req: SubstituteRequest, strict=False):
    title = req.substitutes[0] + " 없는 레시피" if req.serving == "" else f"{req.substitutes[0]} 없는 {req.serving} 기준 레시피"
    ingredients_str = "\n".join(req.ingredients)
    steps_str = "\n".join(f"{i+1}. {s}" for i, s in enumerate(req.steps))
    substitutes_str = ", ".join(req.substitutes)

    prompt = (
        f"당신은 한국 요리 전문가입니다. 다음 레시피에서 특정 재료를 대체할 수 있는 방법을 제시해주세요.\n\n"
        
        f"[레시피 정보]\n"
        f"제목: {title}\n"
        f"인분: {req.serving}\n\n"
        
        f"[전체 재료]\n{ingredients_str}\n\n"
        f"[조리 순서]\n{steps_str}\n\n"
        
        f"[대체 필요한 재료]\n{substitutes_str}\n\n"
        
        f"위 재료들에 대해서만 대체안을 제시해주세요.\n\n"
        
        f"**한국 요리 대체재료 가이드:**\n"
        f"- 간장: 소금 + 설탕, 굴소스, 된장 소량\n"
        f"- 고추장: 고춧가루 + 된장 + 설탕, 케찹 + 고춧가루\n"
        f"- 마늘: 마늘가루, 양파, 생강\n"
        f"- 양파: 대파, 쪽파, 마늘\n"
        f"- 설탕: 꿀, 올리고당, 물엿, 메이플시럽\n"
        f"- 참기름: 들기름, 올리브오일\n"
        f"- 식초: 레몬즙, 매실액\n\n"
        
        f"**출력 형식:**\n"
        f"{{\n"
        f'  "ingredients": [\n'
        f'    "재료명: 대체안1 양 | 대체안2 양",\n'
        f'    "재료명: 양 (생략 가능)",\n'
        f'    "재료명: 양 (대체 불가)"\n'
        f'  ]\n'
        f"}}\n\n"
        
        f"**주의사항:**\n"
        f"1. 각 대체안에는 반드시 구체적인 양을 포함하세요\n"
        f"2. 여러 대체안은 '|'로 구분하세요\n"
        f"3. 대체가 어려우면 '생략 가능' 또는 '대체 불가'로 표시하세요\n"
        f"4. 요리의 맛과 질감을 고려한 현실적인 대체안을 제시하세요\n"
        f"5. **중복된 재료는 절대 제시하지 마세요** (예: 마늘가루를 두 번 제시하면 안됨)\n"
        f"6. 서로 다른 재료를 제시하세요 (마늘가루, 생강, 양파 등)\n"
    )
    return prompt

def is_placeholder(value: str) -> bool:
    if not value:
        return True
    pattern = re.compile(r"(대체안\d*|정량|양|대체재|없음|생략 가능)")
    return bool(pattern.search(value))

def normalize_parentheses(val: str) -> str:
    val = re.sub(r'\(*\s*(대체 불가|생략 가능)\s*\)*', r'(\1)', val)
    val = re.sub(r'\)\)+', ')', val)
    return val

async def get_substitute_response(req: SubstituteRequest, strict=False):
    prompt = build_prompt(req, strict)
    response = await client.chat.completions.create(
        model="gpt-3.5-turbo",  
        messages=[
            {"role": "system", "content": "당신은 한국 요리 전문가입니다. 한국인의 입맛과 일반적인 한국 가정의 재료 보유 현황을 잘 알고 있습니다."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.7, 
        max_tokens=2000,
    )
    content = response.choices[0].message.content.strip()
    if "{" in content:
        content = content[content.find("{"):]
    parsed = json.loads(content)
    return {"parsed": parsed}

async def async_request_final_judgment(ingredient: str, amount: str, steps: list[str]) -> str:
    if any(kw in amount for kw in ["비정량", "약간", "적당량", "소량"]):
        return "생략 가능"

    steps_str = "\n".join(f"{i+1}. {s}" for i, s in enumerate(steps))
    prompt = (
        f"다음 재료가 레시피에서 누락되었거나 대체안이 불확실합니다.\n"
        f"- 재료명: {ingredient}\n"
        f"- 원래 양: {amount}\n\n"
        f"이 재료는 생략 가능한지, 아니면 반드시 필요한데 대체 불가능한지를 판단해 주세요.\n"
        f"출력은 반드시 아래 중 하나만 포함해야 합니다:\n"
        f"- 생략 가능\n"
        f"- 대체 불가\n\n"
        f"레시피 조리 순서:\n{steps_str}"
    )

    response = await client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "당신은 요리 전문가입니다."},
            {"role": "user", "content": prompt},
        ],
        temperature=0,
        max_tokens=100,
    )
    return response.choices[0].message.content.strip()

async def async_get_substitute(sub: str, req: SubstituteRequest) -> tuple[str, str]:
    collected_raw = []
    max_attempts = 6  # 더 많은 시도로 품질 향상
    attempts = 0

    def is_placeholder(value: str) -> bool:
        # 더 정확한 플레이스홀더 감지
        pattern = re.compile(r"(대체안\d*|정량|양|대체재|없음|생략\s*가능|대체\s*불가|대체불가|불가능|적절하지|모르겠)", re.IGNORECASE)
        return bool(pattern.search(value))

    def normalize_key(text: str) -> str:
        # 재료명만 추출하여 중복 체크 (양과 단위는 유지)
        text = text.lower().strip()
        text = re.sub(r"\([^)]*\)", "", text)  # 괄호 제거
        
        # 일반적인 단위들을 기준으로 재료명만 추출
        units = ['큰술', '큰스푼', 't', 'T', '작은술', '작은스푼', 'tsp', '개', '쪽', '조각', 'g', 'ml', 'kg', 'l']
        
        # 단위 앞의 숫자와 단위를 제거
        for unit in units:
            pattern = rf'\s*\d+\.?\d*\s*{re.escape(unit)}\s*'
            text = re.sub(pattern, '', text, flags=re.IGNORECASE)
        
        # 남은 숫자들 제거
        text = re.sub(r'\d+\.?\d*', '', text)
        text = re.sub(r'\s+', ' ', text)  # 여러 공백을 하나로
        
        return text.strip()

    def are_similar_ingredients(ing1: str, ing2: str) -> bool:
        """두 재료가 비슷한지 확인 (중복 방지용)"""
        norm1 = normalize_key(ing1)
        norm2 = normalize_key(ing2)
        
        # 정확히 같은 재료명
        if norm1 == norm2:
            return True
            
        # 하나가 다른 하나를 포함하는 경우 (예: "마늘" vs "마늘가루")
        if norm1 in norm2 or norm2 in norm1:
            return True
            
        return False

    while len(collected_raw) < 3 and attempts < max_attempts:
        result = await get_substitute_response(SubstituteRequest(
            ingredients=req.ingredients,
            steps=req.steps,
            substitutes=[sub],
            serving=req.serving
        ))

        ingredients_list = result["parsed"].get("ingredients", [])

        #print(f"\n GPT 응답 #{attempts+1} for '{sub}':")
        #print(json.dumps(result["parsed"], ensure_ascii=False, indent=2))

        for i in ingredients_list:
            if ":" not in i:
                continue
            name, raw_val = i.split(":", 1)
            name = name.strip()
            val = raw_val.strip()
            if name != sub:
                continue

            options = [v.strip() for v in val.split("|")]
            for opt in options:
                if not is_placeholder(opt):
                    # 기존에 수집된 재료와 유사한지 확인
                    is_duplicate = any(are_similar_ingredients(opt, existing) for existing in collected_raw)
                    
                    if not is_duplicate:
                        collected_raw.append(opt)

        attempts += 1

    #print(f"\n 최종 대체안 for '{sub}': {collected_raw if collected_raw else '없음'}")

    if not collected_raw:
        original_amount = next(
            (i.split(":", 1)[1].strip() for i in req.ingredients if i.startswith(sub + ":")),
            ""
        )
        judgment = await async_request_final_judgment(sub, original_amount, req.steps)
        if judgment == "생략 가능":
            return sub, f"{original_amount} (생략 가능)"
        else:
            return sub, f"{original_amount} (대체 불가)"
    else:
        return sub, normalize_parentheses(" | ".join(collected_raw))

@router.post("/substitute")
async def recommend_substitute(req: SubstituteRequest):
    try:
        #print(" 받은 요청 데이터:")
        #print("substitutes:", req.substitutes)

        # GPT에 개별 비동기 요청
        tasks = [async_get_substitute(sub, req) for sub in req.substitutes]
        results = await asyncio.gather(*tasks)

        parsed_dict = {key: val for key, val in results}

        merged_ingredients = []
        already_handled = set()

        for item in req.ingredients:
            if ":" not in item:
                continue
            k, v = item.split(":", 1)
            key = k.strip()
            original_val = v.strip()

            if key in already_handled:
                continue  

            if key in parsed_dict:
                val = parsed_dict[key]
                if val.strip() == "(대체 불가)":
                    merged_ingredients.append(f"{key}: {original_val} (대체 불가)")
                elif val.endswith("(생략 가능)"):
                    merged_ingredients.append(f"{key}: {original_val} (생략 가능)")
                else:
                    merged_ingredients.append(f"{key}: {val}")
            else:
                merged_ingredients.append(f"{key}: {original_val}")
            
            already_handled.add(key)

        final_result = {
            "ingredients": merged_ingredients
        }

        #print("\n 최종 응답 내용:")
        #print(json.dumps(final_result, ensure_ascii=False, indent=2))

        return {"result": final_result}

    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"error": str(e)}
