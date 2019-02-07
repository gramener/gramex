---
title: GroupMeans analyzes root causes
prefix: GroupMeans
...

[TOC]

## Root cause analysis

Root Cause Analysis is the process of determining what factors affect a particular metric or set of metrics the most.
In this dataset of National Achievement Survey results of class 8th Students from 2014, we want to determine which factors affect a students marks the most.

<sub>In case the following analysis throws an error - please click the subsequent button to download the appropriate datafile</sub>

<button id="dl-data">Download data for this example</button>

<script>
$('body').on('click', '#dl-data', function () {
  $.ajax('download-data', function(){})
  window.location.reload()
})
</script>

<iframe class="w-100" src="nas?_format=table&_limit=5&_c=Gender&_c=Age&_c=Father edu&_c=Maths %&_c=Reading %&_c=Science %&_c=Social %&_c=Total %"></iframe>

Here's the distribution  two columns in our dataset, Gender and the Father's Education across all the student's marks.
By some examination, we can see there isn't much difference between the average scores between girls and boys, leading us to believe that Gender is perhaps not very impactful on the students' marks.

On the other hand, as the father's education increases from illiteracy to a college degree or better, both girls' and boys' average scores increase steadily.
Thus Father's Education probably has a strong impact on a student's marks.

<iframe class="w-100" src="nas?&_limit=100000&_sort=Father%20edu&_by=Gender&_by=Father%20edu&_c=Maths%20%25|avg&_c=Reading%20%25|avg&_c=Science%20%25|avg&_c=Social%20%25|avg&_c=Total%20%25|avg&_format=table"></iframe>

Groupmeans is a service that extends this idea to all factors.
It can be used to quickly identify the most significant factors onto a metric along with a confidence interval for each result.

<iframe class="w-100" src="table.html?groups=Gender&groups=Father%20edu&numbers=Maths%20%"></iframe>

## Exploratory analysis

<div class="example">
  <a class="example-demo" href="form.html">Explore the data yourself</a>
  <a class="example-src" href="http://github.com/gramener/gramex/tree/master/gramex/apps/guide/groupmeans/">Source</a>
</div>

<!-- TODO: Allow users to pick from a pre-defined set of segments: Boys/Girls. Below Poverty, Siblings -->

## Upload your data

<div class="example">
  <a class="example-demo" href="custom-explore">Upload your own csv and explore</a>
  <a class="example-src" href="http://github.com/gramener/gramex/tree/master/gramex/apps/guide/groupmeans/">Source</a>
</div>
