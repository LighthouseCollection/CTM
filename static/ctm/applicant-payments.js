/* Owner payment facts only; this view never grants filing or records provider success. */
(() => {
  "use strict";
  const states={fee:["due","paid","waived","historical_exempt"],
    checkout:["pending","processing","paid","needs_review","finalized","expired","failed"],
    event:["paid","refunded","chargeback","dispute_won","dispute_lost"]};
  const statusKey=(value,kind)=>states[kind]?.includes(value) ? value : "unknown";
  const amount=row=>Number.isSafeInteger(row?.amount_minor)&&row.amount_minor>=0&&row.currency==="USD";
  const timestamp=value=>typeof value==="string"&& /(?:Z|[+-]\d{2}:\d{2})$/.test(value)&&Number.isFinite(Date.parse(value));
  function validProjection(data) {
    const rows=(items,test)=>Array.isArray(items)&&items.every(row=>row&&typeof row.id==="string"&&!!row.id&&test(row))&&
      new Set(items.map(row=>row.id)).size===items.length;
    return !!data&&amount(data.fee)&&typeof data.fee.status==="string"&&typeof data.verified_payment==="boolean"&&
      rows(data.checkouts,row=>typeof row.state==="string"&&Number.isSafeInteger(row.version)&&row.version>0&&timestamp(row.timestamp))&&
      rows(data.events,row=>amount(row)&&typeof row.kind==="string"&&timestamp(row.timestamp)&&
        row.amount_basis===(row.kind==="refunded"?"cumulative_refunded":"event"));
  }
  const words={
    en:{title:"Payment status and history",refresh:"Refresh payment history",loading:"Loading payment history…",
      unavailable:"Payment history is unavailable. Refresh or contact the tribunal.",fee:"Application fee",
      due:"Payment due",paid:"Verified payment recorded",waived:"Authorized fee waiver",historical_exempt:"Historical filing exemption",
      verified:"A verified provider payment is recorded.",unverified:"No verified provider payment is recorded. An authorized waiver does not count as a provider payment.",
      separate:"Payment history does not confirm filing. Check the application status above for submission progress.",
      attempts:"Checkout history",events:"Payment events",none:"No payment events or checkout attempts are recorded.",
      version:"Answer version",pending:"Checkout pending",processing:"Payment processing",needs_review:"Payment requires tribunal reconciliation",
      finalized:"Payment applied to filing",expired:"Checkout expired",failed:"Checkout failed",refunded:"Refund recorded",
      chargeback:"Payment dispute opened",dispute_won:"Payment dispute resolved in tribunal’s favour",dispute_lost:"Payment dispute lost",
      cumulative:"Cumulative refunded total",unknown:"Status unavailable"},
    ar:{title:"حالة الدفع وسجله",refresh:"تحديث سجل الدفع",loading:"جارٍ تحميل سجل الدفع…",
      unavailable:"سجل الدفع غير متاح. حدّث السجل أو تواصل مع المجلس.",fee:"رسوم الطلب",
      due:"الدفع مطلوب",paid:"تم تسجيل دفعة موثّقة",waived:"إعفاء معتمد من الرسوم",historical_exempt:"إعفاء لطلب تاريخي",
      verified:"تم تسجيل دفعة موثّقة لدى مزود الدفع.",unverified:"لم يتم تسجيل دفعة موثّقة لدى مزود الدفع. الإعفاء المعتمد ليس دفعة لدى مزود الدفع.",
      separate:"سجل الدفع لا يؤكد تقديم الطلب. راجع حالة الطلب أعلاه لمعرفة تقدم التقديم.",
      attempts:"سجل محاولات الدفع",events:"أحداث الدفع",none:"لا توجد أحداث دفع أو محاولات دفع مسجلة.",
      version:"نسخة الإجابات",pending:"محاولة الدفع قيد الانتظار",processing:"الدفع قيد المعالجة",needs_review:"تتطلب الدفعة مراجعة وتسوية لدى المجلس",
      finalized:"تم تطبيق الدفعة على تقديم الطلب",expired:"انتهت صلاحية محاولة الدفع",failed:"فشلت محاولة الدفع",refunded:"تم تسجيل استرداد",
      chargeback:"تم فتح نزاع على الدفعة",dispute_won:"تم حسم نزاع الدفع لصالح المجلس",dispute_lost:"تم حسم نزاع الدفع ضد المجلس",
      cumulative:"إجمالي المبلغ المسترد التراكمي",unknown:"الحالة غير متاحة"}
  };
  function PaymentHistory({applicationId,api,lang="en",refreshKey=0}) {
    const R=window.React,P=window.Plenix,h=R.createElement,t=key=>words[lang==="ar"?"ar":"en"][key];
    const [data,setData]=R.useState(null),[loading,setLoading]=R.useState(true),[error,setError]=R.useState(false),[revision,reload]=R.useState(0);
    R.useEffect(()=>{
      let active=true;setData(null);setError(false);setLoading(true);
      api(`/api/applications/${encodeURIComponent(applicationId)}/payments/`).then(result=>{
        if(!validProjection(result))throw new Error("Invalid payment projection");
        if(active)setData(result);
      }).catch(()=>{if(active)setError(true);}).finally(()=>{if(active)setLoading(false);});
      return()=>{active=false;};
    },[applicationId,api,revision,refreshKey]);
    const money=row=>new Intl.NumberFormat(lang==="ar"?"ar":"en",{style:"currency",currency:"USD"}).format(row.amount_minor/100);
    return h(P.Panel,{ icon: "doc-text",title:t("title")},h(P.Stack,null,
      h(P.Button,{disabled:loading,onClick:()=>reload(n=>n+1)},t("refresh")),
      loading?h(P.Text,{role:"status"},t("loading")):null,
      error?h(P.Notice,{tone:"danger",role:"alert"},t("unavailable")):null,
      data?h(P.Stack,null,
        h(P.Text,null,`${t("fee")}: ${money(data.fee)} · ${t(statusKey(data.fee.status,"fee"))}`),
        h(P.Text,null,t(data.verified_payment?"verified":"unverified")),h(P.Notice,null,t("separate")),
        !data.events.length&&!data.checkouts.length?h(P.Text,null,t("none")):null,
        data.checkouts.length?h(P.Panel,{ icon: "doc-text",title:t("attempts")},h(P.Stack,null,...data.checkouts.map(row=>
          h(P.Stack,{key:row.id},h(P.Text,null,`${t(statusKey(row.state,"checkout"))} · ${t("version")}: ${row.version}`),
            h(P.Text,null,h("bdi",{dir:"ltr"},row.timestamp)))))):null,
        data.events.length?h(P.Panel,{ icon: "doc-text",title:t("events")},h(P.Stack,null,...data.events.map(row=>
          h(P.Stack,{key:row.id},h(P.Text,null,`${t(statusKey(row.kind,"event"))} · ${money(row)}`),
            row.amount_basis==="cumulative_refunded"?h(P.Text,null,t("cumulative")):null,
            h(P.Text,null,h("bdi",{dir:"ltr"},row.timestamp)))))):null):null));
  }
  window.CTMApplicantPayments={validProjection,statusKey,PaymentHistory};
})();
