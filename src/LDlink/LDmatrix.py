#!/usr/bin/env python

# Create LDmatrix function
def calculate_matrix(snplst,pop,request):
	import json,math,operator,os,sqlite3,subprocess,sys,time
	start_time=time.time()
	
	# Set data directories
	data_dir="/local/content/ldlink/data/"
	snp_dir=data_dir+"snp141/snp141.db"
	pop_dir=data_dir+"1000G/Phase3/samples/"
	vcf_dir=data_dir+"1000G/Phase3/genotypes/ALL.chr"
	tmp_dir="./tmp/"
	
	
	# Ensure tmp directory exists
	if not os.path.exists(tmp_dir):
		os.makedirs(tmp_dir)
	
	
	# Create JSON output 
	output={}
	
	
	# Open SNP list file
	snps=open(snplst).readlines()
	if len(snps)>100:
		output["error"]="Maximum SNP list is 100 SNPs. Your list contains "+str(len(snps))+" entries."
		return(json.dumps(output, sort_keys=True, indent=2),None,None)
		raise
	
	
	# Find coordinates (GRCh37/hg19) for SNP RS number
	# Connect to snp141 database
	conn=sqlite3.connect(snp_dir)
	conn.text_factory=str
	cur=conn.cursor()
	
	
	# Select desired ancestral populations
	pops=pop.split("+")
	pop_dirs=[]
	for pop_i in pops:
		if pop_i in ["ALL","AFR","AMR","EAS","EUR","SAS","ACB","ASW","BEB","CDX","CEU","CHB","CHS","CLM","ESN","FIN","GBR","GIH","GWD","IBS","ITU","JPT","KHV","LWK","MSL","MXL","PEL","PJL","PUR","STU","TSI","YRI"]:
			pop_dirs.append(pop_dir+pop_i+".txt")
		else:
			output["error"]=pop_i+" is not an ancestral population. Choose one of the following ancestral populations: AFR, AMR, EAS, EUR, or SAS; or one of the following sub-populations: ACB, ASW, BEB, CDX, CEU, CHB, CHS, CLM, ESN, FIN, GBR, GIH, GWD, IBS, ITU, JPT, KHV, LWK, MSL, MXL, PEL, PJL, PUR, STU, TSI, or YRI."
			return(json.dumps(output, sort_keys=True, indent=2),None,None)
			raise
	
	get_pops="cat "+ " ".join(pop_dirs) +" > "+tmp_dir+"pops_"+request+".txt"
	subprocess.call(get_pops, shell=True)
	
	pop_list=open(tmp_dir+"pops_"+request+".txt").readlines()
	ids=[]
	for i in range(len(pop_list)):
		ids.append(pop_list[i].strip())
	
	pop_ids=list(set(ids))
	
	
	
	# Find RS numbers in snp141 database
	rs_nums=[]
	snp_pos=[]
	snp_coords=[]
	warn=[]
	tabix_coords=""
	for i in range(len(snps)):
		snp_i=snps[i].strip().split()
		if len(snp_i)>0:
			if len(snp_i[0])>2:
				if snp_i[0][0:2]=="rs":
					id="99"+(13-len(snp_i[0]))*"0"+snp_i[0].strip("rs")
					cur.execute('SELECT * FROM snps WHERE id=?', (id,))
					snp_coord=cur.fetchone()
					if snp_coord!=None:
						rs_nums.append(snp_i[0])
						snp_pos.append(snp_coord[3])
						temp=[snp_coord[1],snp_coord[2],snp_coord[3]]
						snp_coords.append(temp)
						temp2=snp_coord[2]+":"+snp_coord[3]+"-"+snp_coord[3]
						tabix_coords=tabix_coords+" "+temp2
					else:
						warn.append(snp_i[0])
	
	if warn!=[]:
		output["warning"]="Not all input SNPs were found in dbSNP 141 ("+",".join(warn)+")"
	
	
	# Check SNPs are all on the same chromosome
	for i in range(len(snp_coords)):
		if snp_coords[0][1]!=snp_coords[i][1]:
			output["error"]="Not all input SNPs are on the same chromosome"
			return(json.dumps(output, sort_keys=True, indent=2),None,None)
			raise
	
	
	# Extract 1000 Genomes phased genotypes
	vcf_file=vcf_dir+snp_coord[2]+".phase3_shapeit2_mvncall_integrated_v5.20130502.genotypes.vcf.gz"
	tabix_snps="tabix -fh {0}{1} > {2}".format(vcf_file, tabix_coords, tmp_dir+"snps_"+request+".vcf")
	subprocess.call(tabix_snps, shell=True)
	grep_remove_dups="grep -v -e END "+tmp_dir+"snps_"+request+".vcf > "+tmp_dir+"snps_no_dups_"+request+".vcf"
	subprocess.call(grep_remove_dups, shell=True)
	
	
	# Import SNP VCF files
	vcf=open(tmp_dir+"snps_no_dups_"+request+".vcf").readlines()
	h=0
	while vcf[h][0:2]=="##":
		h+=1
	
	head=vcf[h].strip().split()
	
	# Extract haplotypes
	index=[]
	for i in range(9,len(head)):
		if head[i] in pop_ids:
			index.append(i)
	
	hap1=[""]*len(index)
	hap2=[""]*len(index)
	rsnum_lst=[]
	allele_lst=[]
	pos_lst=[]
	for g in range(h+1,len(vcf)):
		geno=vcf[g].strip().split()
		count0=0
		count1=0
		if geno[3] in ["A","C","G","T"] and geno[4] in ["A","C","G","T"]:
			for i in range(len(index)):
				if geno[index[i]]=="0|0":
					hap1[i]=hap1[i]+geno[3]
					hap2[i]=hap2[i]+geno[3]
					count0+=2
				elif geno[index[i]]=="0|1":
					hap1[i]=hap1[i]+geno[3]
					hap2[i]=hap2[i]+geno[4]
					count0+=1
					count1+=1
				elif geno[index[i]]=="1|0":
					hap1[i]=hap1[i]+geno[4]
					hap2[i]=hap2[i]+geno[3]
					count0+=1
					count1+=1
				elif geno[index[i]]=="1|1":
					hap1[i]=hap1[i]+geno[4]
					hap2[i]=hap2[i]+geno[4]
					count1+=2
				elif geno[index[i]]=="./.":
					hap1[i]=hap1[i]+"."
					hap2[i]=hap2[i]+"."
				else:
					hap1[i]=hap1[i]+"?"
					hap2[i]=hap2[i]+"?"
			
			if geno[1] in snp_pos:
				rsnum=rs_nums[snp_pos.index(geno[1])]
			else:
				rsnum=str(g)+"?"
			rsnum_lst.append(rsnum)
			
			position="chr"+geno[0]+":"+geno[1]+"-"+geno[1]
			pos_lst.append(position)
			alleles=geno[3]+"/"+geno[4]
			allele_lst.append(alleles)
	
	# Calculate Pairwise LD Statistics
	all_haps=hap1+hap2
	ld_matrix=[[[None for v in range(2)] for i in range(len(all_haps[0]))] for j in range(len(all_haps[0]))]
	
	for i in range(len(all_haps[0])):
		for j in range(i,len(all_haps[0])):
			hap={}
			for k in range(len(all_haps)):
				# Extract haplotypes
				hap_k=all_haps[k][i]+all_haps[k][j]
				if hap_k in hap:
					hap[hap_k]+=1
				else:
					hap[hap_k]=1
			
			# Check all haplotypes are present
			if len(hap)!=4:
				snp_i_a=allele_lst[i].split("/")
				snp_j_a=allele_lst[j].split("/")
				haps=[snp_i_a[0]+snp_j_a[0],snp_i_a[0]+snp_j_a[1],snp_i_a[1]+snp_j_a[0],snp_i_a[1]+snp_j_a[1]]
				for h in haps:
					if h not in hap:
						hap[h]=0
			
			# Perform LD calculations
			A=hap[sorted(hap)[0]]
			B=hap[sorted(hap)[1]]
			C=hap[sorted(hap)[2]]
			D=hap[sorted(hap)[3]]
			delta=float(A*D-B*C)
			Ms=float((A+C)*(B+D)*(A+B)*(C+D))
			if Ms!=0:
				# D prime
				if delta<0:
					D_prime=round(delta/min((A+C)*(A+B),(B+D)*(C+D)),3)
				else:
					D_prime=round(delta/min((A+C)*(C+D),(A+B)*(B+D)),3)
				
				# R2
				r2=round((delta**2)/Ms,3)
				
				# Find Correlated Alleles
				if r2>0.1:
					N=A+B+C+D
					# Expected Cell Counts
					eA=(A+B)*(A+C)/N
					eB=(B+A)*(B+D)/N
					eC=(C+A)*(C+D)/N
					eD=(D+C)*(D+B)/N
					
					# Calculate Deltas
					dA=(A-eA)**2
					dB=(B-eB)**2
					dC=(C-eC)**2
					dD=(D-eD)**2
					dmax=max(dA,dB,dC,dD)
					
					if dmax==dA or dmax==dD:
						match=sorted(hap)[0][0]+"-"+sorted(hap)[0][1]+","+sorted(hap)[2][0]+"-"+sorted(hap)[1][1]
					else:
						match=sorted(hap)[0][0]+"-"+sorted(hap)[1][1]+","+sorted(hap)[2][0]+"-"+sorted(hap)[0][1]
				else:
					match="  -  ,  -  "
			
			snp1=rsnum_lst[i]
			snp2=rsnum_lst[j]
			pos1=pos_lst[i].split("-")[0]
			pos2=pos_lst[j].split("-")[0]
			allele1=allele_lst[i]
			allele2=allele_lst[j]
			corr=match.split(",")[0].split("-")[1]+"-"+match.split(",")[0].split("-")[0]+","+match.split(",")[1].split("-")[1]+"-"+match.split(",")[1].split("-")[0]
			corr_f=match
			ld_matrix[i][j]=[snp1,snp2,allele1,allele2,corr,pos1,pos2,D_prime,r2]
			ld_matrix[j][i]=[snp2,snp1,allele2,allele1,corr_f,pos2,pos1,D_prime,r2]
	
	
	# Generate D' and R2 output matrices
	d_matrix=[]
	r_matrix=[]
		
	d_matrix.append("RS_number"+"\t"+"\t".join(rsnum_lst))
	r_matrix.append("RS_number"+"\t"+"\t".join(rsnum_lst))
	
	dim=len(ld_matrix)
	for i in range(dim):
		temp_d=[rsnum_lst[i]]
		temp_r=[rsnum_lst[i]]
		for j in range(dim):
			temp_d.append(str(ld_matrix[i][j][7]))
			temp_r.append(str(ld_matrix[i][j][8]))
		d_matrix.append("\t".join(temp_d))
		r_matrix.append("\t".join(temp_r))
	
	output["d_matrix"]=d_matrix
	output["r_matrix"]=r_matrix
	
	out_json=json.dumps(output, sort_keys=True, indent=2)
	
	
	# Generate Plot Variables
	out=[j for i in ld_matrix for j in i]
	xnames=[]
	ynames=[]
	xA=[]
	yA=[]
	corA=[]
	xpos=[]
	ypos=[]
	D=[]
	R=[]
	
	for i in range(len(out)):
		snp1,snp2,allele1,allele2,corr,pos1,pos2,D_prime,r2=out[i]
		xnames.append(snp1)
		ynames.append(snp2)
		xA.append(allele1)
		yA.append(allele2)
		corA.append(corr)
		xpos.append(pos1)
		ypos.append(pos2)
		D.append(D_prime)
		R.append(r2)
	
	# Import plotting modules
	import bokeh.embed as embed
	from bokeh.objects import HoverTool
	from bokeh.plotting import axis,ColumnDataSource,curplot,figure,grid,rect,xaxis
	from bokeh.resources import CDN
	from collections import OrderedDict
	
	source = ColumnDataSource(
		data=dict(
			xname=xnames,
			yname=ynames,
			xA=xA,
			yA=yA,
			xpos=xpos,
			ypos=ypos,
			R2=R,
			Dp=D,
			corA=corA,
		)
	)
	
	figure(outline_line_color="white")
	rect('xname', 'yname', 0.95, 0.95, source=source,
		 x_axis_location="above",
		 x_range=rsnum_lst, y_range=list(reversed(rsnum_lst)),
		 color="red", alpha="R2", line_color=None,
		 tools="hover,previewsave", title=" ",
		 plot_width=800, plot_height=800)
	
	grid().grid_line_color=None
	axis().axis_line_color=None
	axis().major_tick_line_color=None
	axis().major_label_text_font_size=str(15-len(rsnum_lst)/10)+"pt"
	axis().major_label_text_font_style="normal"
	axis().major_label_standoff=0
	xaxis().major_label_orientation="vertical"
	
	hover=curplot().select(dict(type=HoverTool))
	hover.tooltips=OrderedDict([
		("SNP 1", "@yname (@yA)"),
		("SNP 2", "@xname (@xA)"),
		("D prime", "@Dp"),
		("R2", "@R2"),
		("Correlated Alleles", "@corA"),
	])
	
	out_script,out_div=embed.components(curplot(), CDN)
	
	
	# Print run time
	duration=time.time()-start_time
	print ""
	print "Run time: "+str(duration)+" seconds\n"
	
	# Remove temporary files
	subprocess.call("rm "+tmp_dir+"pops_"+request+".txt", shell=True)
	subprocess.call("rm "+tmp_dir+"*_"+request+".vcf", shell=True)
	
	
	# Return output
	return(out_json,out_script,out_div)


def main():
	import json,sys
	
	# Import LDmatrix options
	if len(sys.argv)==4:
		snplst=sys.argv[1]
		pop=sys.argv[2]
		request=sys.argv[3]
	else:
		print "Correct useage is: LDmatrix.py snplst populations request"
		sys.exit()
	
	
	# Run function
	out_json,out_script,out_div=calculate_matrix(snplst,pop,request)
	
	
	# Print output
	json_dict=json.loads(out_json)
	
	try:
		json_dict["error"]
	
	except KeyError:
		d_matrix=json_dict["d_matrix"]
		print "D Prime:"
		for i in range(len(d_matrix)):
			print d_matrix[i]
		print ""
		
		r_matrix=json_dict["r_matrix"]
		print "R2:"
		for i in range(len(r_matrix)):
			print r_matrix[i]
		print ""
		
		out_script_line=out_script.split("\n")
		for i in range(len(out_script_line)):
			if len(out_script_line[i])<110:
				print out_script_line[i]
			else:
				print out_script_line[i][0:110]
		print ""
		
		print out_div

		
		try:
			json_dict["warning"]
		except KeyError:
			print ""
		else:
			print ""
			print "WARNING: "+json_dict["warning"]+"!"
			print ""
	
	else:
		print ""
		print json_dict["error"]
		print ""

if __name__ == "__main__":
	main()