import numpy as np
import scipy.stats as stats
import matplotlib.pyplot as plt

h = sorted([186, 176, 158, 180, 186, 168, 168, 164, 178, 170, 189, 195, 172,
     187, 180, 186, 185, 168, 179, 178, 183, 179, 170, 175, 186, 159,
     161, 178, 175, 185, 175, 162, 173, 172, 177, 175, 172, 177, 180])  #sorted

fit = stats.norm.pdf(h, np.mean(h), np.std(h))  #this is a fitting indeed

figure = plt.figure()
plt.plot(h, fit,'-o')

plt.title("Semantic paths length distribution")
plt.xlabel("Sematnic path length")
plt.ylabel("Amout of paths,")

plt.hist(h, normed=True)      #use this to draw histogram of your data



plt.show()                   #use may also need add this
figure.savefig("eval-subs-distribution.pdf", bbox_inches='tight')