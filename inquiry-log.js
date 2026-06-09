// ── Inquiry / request history (append-only push log, merged by id) ───────────
// One line = one push. Pushing the same id again MERGES fields (overwrite/fill) —
// that's how a status transition is recorded without rewriting earlier lines.
// Append via: log-inquiry.py  (do NOT hand-edit — use the helper, see README).
//   ① receive:  python log-inquiry.py --new --type simple --q "..." --by alice --req "requester/team"  → prints id
//   ② transit:  python log-inquiry.py --id <that id> --status in-progress|waiting
//   ③ done:     python log-inquiry.py --done --id <that id> --a "resolution" --ref "#anchor"
// fields: {id, date, type, q, a, by(logger), req(requester/team — chip next to id), ref, status:"received"|"in-progress"|"waiting"|"done"}
//
// ⚠️ All entries below are FICTIONAL sample data for demo purposes.
window.INQUIRY_LOG = window.INQUIRY_LOG || [];

// — a simple inquiry answered immediately —
window.INQUIRY_LOG.push({id:"INQ-260104-091500", date:"2026-01-04", type:"simple", q:"How do I look up a user's employee number?", a:"Use the user master display (SU01D) and check the address tab.", by:"alice", req:"bob / sales", ref:"#tcode-master", status:"done"});

// — a request that moved received -> in-progress -> done (3 pushes, merged by id) —
window.INQUIRY_LOG.push({id:"INQ-260105-101200", date:"2026-01-05", type:"request", q:"Sales order SO-1001 delivery date needs to change; tax invoice already issued.", by:"alice", req:"carol / sales", status:"received"});
window.INQUIRY_LOG.push({id:"INQ-260105-101200", status:"in-progress", ref:"#proc-sales-cancel"});
window.INQUIRY_LOG.push({id:"INQ-260105-101200", status:"done", a:"Cancelled via ZSD030 (credit memo path), then re-billed under a new SO. Same accounting period -> no closing impact."});

// — an urgent issue still in progress —
window.INQUIRY_LOG.push({id:"INQ-260106-085400", date:"2026-01-06", type:"urgent", q:"ABAP dump when issuing a corrective (minus) tax invoice — month-end, urgent.", by:"alice", req:"dave / finance", status:"received"});
window.INQUIRY_LOG.push({id:"INQ-260106-085400", status:"in-progress", a:"Reproduced. Likely a number-conversion error in the document-text split. Checking ST22.", ref:"#ts-tax-invoice"});

// — a request waiting on another team —
window.INQUIRY_LOG.push({id:"INQ-260107-140000", date:"2026-01-07", type:"request", q:"Reset password for a shared SAP account.", by:"alice", req:"erin / accounting", status:"received"});
window.INQUIRY_LOG.push({id:"INQ-260107-140000", status:"waiting", a:"Password reset is owned by the Basis team — handed off, waiting on their action."});

// — another simple one, just received —
window.INQUIRY_LOG.push({id:"INQ-260108-110000", date:"2026-01-08", type:"simple", q:"Which T-Code shows the monthly billing run?", by:"alice", req:"frank / sales", status:"received"});
