const {test}=require('node:test'),assert=require('node:assert/strict');
const fs=require('node:fs'),vm=require('node:vm');
const context={window:{}};const path='static/ctm/applicant-payments.js';
if(fs.existsSync(path))vm.runInNewContext(fs.readFileSync(path,'utf8'),context);
const P=context.window.CTMApplicantPayments||{};
const data=()=>({fee:{status:'due',amount_minor:25000,currency:'USD'},verified_payment:false,events:[],
 checkouts:[{id:'attempt',state:'processing',version:3,timestamp:'2026-10-21T10:00:00Z'}]});
test('payment projection requires explicit facts and valid amounts/versions',()=>{
 assert.equal(P.validProjection(data()),true);
 for(const mutate of [d=>delete d.verified_payment,d=>d.fee.amount_minor=-1,d=>d.checkouts[0].version=0,
 d=>d.checkouts.push(d.checkouts[0]),d=>d.checkouts[0].timestamp='invalid']){
  const d=data();mutate(d);assert.equal(P.validProjection(d),false);
 }
});
test('waiver is distinct from verified provider payment and unknown states remain unavailable',()=>{
 const d=data();d.fee.status='waived';d.checkouts=[];
 assert.equal(P.validProjection(d),true);assert.equal(P.statusKey('waived','fee'),'waived');
 assert.equal(P.statusKey('new-provider-state','checkout'),'unknown');
 assert.equal(P.statusKey('paid','checkout'),'paid');
 assert.equal(P.statusKey('needs_review','checkout'),'needs_review');
});
test('refund cumulative basis is mandatory and event facts do not change filing status',()=>{
 const d=data();d.events=[{id:'refund',kind:'refunded',amount_minor:5000,currency:'USD',
 amount_basis:'cumulative_refunded',timestamp:'2026-10-21T10:00:00Z'}];
 assert.equal(P.validProjection(d),true);
 d.events[0].amount_basis='event';assert.equal(P.validProjection(d),false);
 assert.equal(P.statusKey('dispute_won','event'),'dispute_won');
});
