import re

with open("src/App.tsx", "r") as f:
    content = f.read()

fixed = re.sub(
    r"const newCase = await createCase\({.*?}\);",
    r"const newCase = await createCase({ merchant_id: 'merchant_123', transaction_id: data.payment_id, amount: data.amount, currency: data.currency, card_network: data.card_network, reason_code: data.reason_code, metadata: { dispute_id: data.dispute_id, respond_by: data.respond_by } } as any);",
    content,
    flags=re.DOTALL
)

with open("src/App.tsx", "w") as f:
    f.write(fixed)
