# Demo Flow

## Goal

Validate a real end-to-end `/chat` flow with a live model and persisted trace.

## Primary demo prompt

```text
Vivo en Sevilla, consumo 500 kWh al mes y tengo un tejado de 8 metros por 5 metros. Quiero una estimación orientativa de cuántos paneles necesito, cuántos caben físicamente, cuánta energía podrían producir en 25 años, si necesito batería, cuánto podría ahorrar y si hay ayudas.
```

## Recovery demo prompt

```text
Vivo en Sevilla y quiero saber cuántos paneles necesito, cuánto ahorraré y si hay ayudas.
```

## Expected outcomes

For the primary flow:

- `/chat` returns `200`
- `trace_id` is present
- `answer_text` is not empty
- the answer stays orientative
- the response distinguishes panels needed by demand from panels that physically fit
- subsidies are not presented as guaranteed grants

For the recovery flow:

- the agent does not fail immediately
- it identifies missing data
- it asks for the smallest missing input or offers explicit scenarios
- it may return a partial result

## Demo sequence

1. Start the API.
2. Send the primary prompt to `POST /chat`.
3. Save the returned `trace_id`.
4. Fetch `GET /traces/{trace_id}`.
5. Review tool calls, warnings, recovery attempts, and the final answer event.
