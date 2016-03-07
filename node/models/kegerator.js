var mongoose = require('mongoose');
var Schema = mongoose.Schema;

var Kegerator = new Schema({
  name: String,
  location: String,
  address: String,
  port: Number
}, {
  timestamps: true
});

module.exports = mongoose.model('Kegerator', Kegerator);
