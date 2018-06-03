library(ggplot2)
library(grDevices)
library(rprojroot)

data(mtcars)
temp <- file.path(dirname(thisfile()), 'gen.plot.png')
png(file=temp, width=512, height=512)
plot(ggplot(mtcars) + aes_string(x='wt') + geom_histogram(bins=10))
dev.off()
temp
