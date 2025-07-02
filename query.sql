
 
with [Resource_CTE] as 
(select 
	[Resource].[ResourceID] as [Resource_ResourceID]
from Erp.Resource as Resource
where (Resource.Company = 'PCE'))

select 
	[JobHead].[JobNum] as [JobHead_JobNum],
	[JobHead].[PartNum] as [JobHead_PartNum],
	[JobHead].[PartDescription] as [JobHead_PartDescription],
	[JobOper].[AssemblySeq] as [JobOper_AssemblySeq],
	[JobAsmbl].[PartNum] as [JobAsmbl_PartNum],
	[JobAsmbl].[Description] as [JobAsmbl_Description],
	[JobAsmbl].[RequiredQty] as [JobAsmbl_RequiredQty],
	[JobOper].[OprSeq] as [JobOper_OprSeq],
	[JobOper].[OpCode] as [JobOper_OpCode],
	[JobOper].[DueDate] as [JobOper_DueDate],
	[JobOper].[EstProdHours] as [JobOper_EstProdHours],
	[JobOper].[EstSetHours] as [JobOper_EstSetHours],
	[JobOper].[RunQty] as [JobOper_RunQty],
	[JobOper].[StartDate] as [JobOper_StartDate],
	[JobOper].[StartHour] as [JobOper_StartHour],
	[JobOper].[ProdStandard] as [JobOper_ProdStandard],
	[JobMtl].[PartNum] as [JobMtl_PartNum],
	[JobMtl].[Description] as [JobMtl_Description],
	[JobMtl].[RequiredQty] as [JobMtl_RequiredQty],
	[JobMtl].[IUM] as [JobMtl_IUM]
from Erp.JobHead as JobHead
inner join Erp.JobOper as JobOper on 
	JobHead.Company = JobOper.Company
	and JobHead.JobNum = JobOper.JobNum
	and ( JobOper.OpComplete = 'FALSE'  and JobOper.LaborEntryMethod <> 'B'  and JobOper.OpCode = 'Saw'  )

left outer join  (select 
	[LaborDtl].[Company] as [LaborDtl_Company],
	[LaborDtl].[JobNum] as [LaborDtl_JobNum],
	[LaborDtl].[AssemblySeq] as [LaborDtl_AssemblySeq],
	[LaborDtl].[OprSeq] as [LaborDtl_OprSeq],
	(SUM(LaborDtl.LaborQty)) as [Calculated_CurQty],
	(COUNT(LaborDtl.SysRowID)) as [Calculated_CrewCount],
	(MIN(LaborDtl.EmployeeNum)) as [Calculated_EmployeeNum]
from Erp.LaborDtl as LaborDtl
where (LaborDtl.ActiveTrans = 'TRUE')

group by [LaborDtl].[Company],
	[LaborDtl].[JobNum],
	[LaborDtl].[AssemblySeq],
	[LaborDtl].[OprSeq])  as LaborDtl_View on 
	JobOper.Company = LaborDtl_View.LaborDtl_Company
	and JobOper.JobNum = LaborDtl_View.LaborDtl_JobNum
	and JobOper.AssemblySeq = LaborDtl_View.LaborDtl_AssemblySeq
	and JobOper.OprSeq = LaborDtl_View.LaborDtl_OprSeq
left outer join  (select 
	[JobProd].[Company] as [JobProd_Company],
	[JobProd].[JobNum] as [JobProd_JobNum],
	[OrderHed].[ShipViaCode] as [OrderHed_ShipViaCode],
	[Customer].[CustNum] as [Customer_CustNum],
	[Customer].[CustID] as [Customer_CustID],
	[Customer].[Name] as [Customer_Name],
	(ROW_NUMBER() OVER(PARTITION BY JobProd.JobNum, OrderHed.OrderNum ORDER BY OrderHed.OrderNum)) as [Calculated_OrderHed_RN]
from Erp.JobProd as JobProd
inner join Erp.OrderHed as OrderHed on 
	JobProd.Company = OrderHed.Company
	and JobProd.OrderNum = OrderHed.OrderNum
inner join Erp.Customer as Customer on 
	OrderHed.Company = Customer.Company
	and OrderHed.CustNum = Customer.CustNum
where (JobProd.OrderNum > 0))  as ShipVia_View on 
	JobOper.Company = ShipVia_View.JobProd_Company
	and JobOper.JobNum = ShipVia_View.JobProd_JobNum
	and ( ShipVia_View.Calculated_OrderHed_RN = 1  )

left outer join Erp.SetupGrp as SetupGrp on 
	JobOper.Company = SetupGrp.Company
	and JobOper.SetupGroup = SetupGrp.SetupGroup
inner join  (select 
	[JobOpDtl].[Company] as [JobOpDtl_Company],
	[JobOpDtl].[JobNum] as [JobOpDtl_JobNum],
	[JobOpDtl].[AssemblySeq] as [JobOpDtl_AssemblySeq],
	[JobOpDtl].[OprSeq] as [JobOpDtl_OprSeq],
	[JobOpDtl].[OpDtlSeq] as [JobOpDtl_OpDtlSeq],
	[JobOpDtl].[SetupOrProd] as [JobOpDtl_SetupOrProd],
	[JobOpDtl].[CapabilityID] as [JobOpDtl_CapabilityID],
	[JobOpDtl].[ResourceGrpID] as [JobOpDtl_ResourceGrpID],
	[JobOpDtl].[ResourceID] as [JobOpDtl_ResourceID],
	[JobOpDtl].[OpDtlDesc] as [JobOpDtl_OpDtlDesc],
	(ROW_NUMBER() OVER(PARTITION BY JobOpDtl.JobNum, JobOpDtl.AssemblySeq, JobOpDtl.OprSeq ORDER BY JobOpDtl.OpDtlSeq)) as [Calculated_JobOpDtl_RN]
from Erp.JobOpDtl as JobOpDtl
where (JobOpDtl.ResourceGrpID = 'CNCTech'))  as JobOpDtl_View on 
	JobOper.Company = JobOpDtl_View.JobOpDtl_Company
	and JobOper.JobNum = JobOpDtl_View.JobOpDtl_JobNum
	and JobOper.AssemblySeq = JobOpDtl_View.JobOpDtl_AssemblySeq
	and JobOper.OprSeq = JobOpDtl_View.JobOpDtl_OprSeq
	and ( JobOpDtl_View.Calculated_JobOpDtl_RN = 1  )

left outer join  (select 
	(STRING_AGG(ResourceID, '~')) as [Calculated_SchResourceList],
	[ResourceTimeUsed].[Company] as [ResourceTimeUsed_Company],
	[ResourceTimeUsed].[JobNum] as [ResourceTimeUsed_JobNum],
	[ResourceTimeUsed].[AssemblySeq] as [ResourceTimeUsed_AssemblySeq],
	[ResourceTimeUsed].[OprSeq] as [ResourceTimeUsed_OprSeq],
	[ResourceTimeUsed].[OpDtlSeq] as [ResourceTimeUsed_OpDtlSeq]
from Erp.ResourceTimeUsed as ResourceTimeUsed
where (ResourceTimeUsed.WhatIf = 'FALSE')

group by [ResourceTimeUsed].[Company],
	[ResourceTimeUsed].[JobNum],
	[ResourceTimeUsed].[AssemblySeq],
	[ResourceTimeUsed].[OprSeq],
	[ResourceTimeUsed].[OpDtlSeq])  as ResourceTimeUsed_View on 
	JobOpDtl_View.JobOpDtl_Company = ResourceTimeUsed_View.ResourceTimeUsed_Company
	and JobOpDtl_View.JobOpDtl_JobNum = ResourceTimeUsed_View.ResourceTimeUsed_JobNum
	and JobOpDtl_View.JobOpDtl_AssemblySeq = ResourceTimeUsed_View.ResourceTimeUsed_AssemblySeq
	and JobOpDtl_View.JobOpDtl_OprSeq = ResourceTimeUsed_View.ResourceTimeUsed_OprSeq
	and JobOpDtl_View.JobOpDtl_OpDtlSeq = ResourceTimeUsed_View.ResourceTimeUsed_OpDtlSeq
inner join Erp.JobAsmbl as JobAsmbl on 
	JobOper.Company = JobAsmbl.Company
	and JobOper.JobNum = JobAsmbl.JobNum
	and JobOper.AssemblySeq = JobAsmbl.AssemblySeq
left outer join Erp.JobMtl as JobMtl on 
	JobAsmbl.Company = JobMtl.Company
	and JobAsmbl.JobNum = JobMtl.JobNum
	and JobAsmbl.AssemblySeq = JobMtl.AssemblySeq
left outer join  (select 
	[PartWip].[Company] as [PartWip_Company],
	[PartWip].[JobNum] as [PartWip_JobNum],
	[PartWip].[AssemblySeq] as [PartWip_AssemblySeq],
	[PartWip].[OprSeq] as [PartWip_OprSeq],
	(SUM(CASE WHEN PartWip.MtlSeq = 0 AND PartWip.TrackType = 'R' THEN PartWip.Quantity ELSE 0 END)) as [Calculated_WIPQty]
from Erp.PartWip as PartWip
group by [PartWip].[Company],
	[PartWip].[JobNum],
	[PartWip].[AssemblySeq],
	[PartWip].[OprSeq])  as PartWip_View on 
	JobOper.Company = PartWip_View.PartWip_Company
	and JobOper.JobNum = PartWip_View.PartWip_JobNum
	and JobOper.AssemblySeq = PartWip_View.PartWip_AssemblySeq
	and JobOper.OprSeq = PartWip_View.PartWip_OprSeq
where (JobHead.JobReleased = 'TRUE'  and JobHead.JobComplete = 'FALSE'  and JobHead.Plant = 'MfgSys')
order by JobOper.StartDate, JobOper.StartHour, JobOper.JobNum, JobOper.AssemblySeq, JobOper.OprSeq, JobOpDtl_View.JobOpDtl_OpDtlSeq