select trx_id, amount
from {{ ref('fact_transaction') }}
where amount < 0
