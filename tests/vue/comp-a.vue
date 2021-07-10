<template>
  <p>{{ greeting }}</p>
</template>

<script>
/* eslint-env node */
module.exports = {
  data() {
    return {
      greeting: "Component: a"
    };
  }
};
</script>

<style scoped>
p {
  font-size: 2em;
  text-align: center;
}
</style>
