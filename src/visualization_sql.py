import matplotlib.pyplot as plt
from matplotlib.cbook import violin_stats
import seaborn as sns
from analysis_sql import metrics

df, volatility, avg_return, corr_coffs = metrics()

plt.figure(figsize=(8, 6))
sns.heatmap(corr_coffs, annot=True, cmap="coolwarm", center=0)
plt.title("Correlation Value Heatmap")
plt.show()

plt.figure(figsize=(8,6))
plt.scatter(volatility, avg_return, s =100)
for id in volatility.index:
    plt.text(volatility[id], avg_return[id], id, fontsize = 12)
plt.title("Return vs Risk")
plt.xlabel("Volatility")
plt.ylabel("avg_return")
plt.show()

