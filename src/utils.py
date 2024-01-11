def hm_to_m(s: str) -> int:
    t = s.split("h")
    return int(t[0]) * 60 + int(t[1])

def m_to_hm(i: int) -> str:
    h = i // 60
    m = i % 60

    sh = str(h)
    if h < 10:
        sh = "0" + sh

    sm = str(m)
    if m < 10:
        sm = "0" + sm

    return sh + "h" + sm