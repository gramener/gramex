---
title: Index of topics
prefix: Search
...

<style>
#search {
  width: 100%;
  padding: 8px;
  margin-bottom: 16px;
  border: 1px solid #ddd;
  box-shadow: 3px 1px 2px #ddd;
}
#searchresults {
  line-height: 2;
}
#index {
  margin-top: 30px;
  border-top: 1px solid #ccc;
  padding-top: 1rem;
  columns: 3;
}
#index a {
  display: block;
  border-bottom: 1px solid transparent;
}
#index a:hover {
  background-color: #eef5ff;
  border-bottom: 1px solid #44546a;
}
</style>

<div><input type="search" id="search" placeholder="Search full text"></div>
<div id="searchresults"></div>
<div id="index"></div>
<script src="../node_modules/lunr/lunr.js"></script>
<script src="search.js?v=3"></script>
