# Create sample data
x <- rnorm(300, mean=0) + rnorm(100, mean=3)
y <- rnorm(300, mean=0) + rnorm(100, mean=3)
norm = data.frame(x, y)

library(grDevices)                                # This library saves to files
temp <- tempfile(fileext='.png')                  # Get a temporary PNG file name
png(file=temp, width=512, height=512)             # Save graphics to temp file
library(ggplot2)                                  # Use ggplot2 for graphics
plot(ggplot(norm) + aes_string(x='x', y='y') + geom_density2d())  # Draw the plot
dev.off()                                         # Stop saving to file
temp                                              # Return the temp file path
