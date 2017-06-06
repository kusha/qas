arr = []
for line in open("interprete2.txt"):
    arr.append(line.rstrip())
for lin in arr:
	if lin.startswith("RECORD"):
		print(lin)